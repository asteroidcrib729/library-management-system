"""Opaque, revocable browser sessions stored in PostgreSQL."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from library_management.domain import UserRole
from library_management.postgres import PostgresDatabase
from library_management.services import AuthenticatedPrincipal


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IssuedSession:
    session_token: str
    csrf_token: str
    principal: AuthenticatedPrincipal
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ActiveSession:
    token_hash: str
    csrf_hash: str
    principal: AuthenticatedPrincipal
    expires_at: datetime

    def csrf_matches(self, token: str) -> bool:
        return hmac.compare_digest(self.csrf_hash, token_digest(token))


class BrowserSessionStore:
    """Own session lifecycle SQL without exposing tokens to domain services."""

    def __init__(
        self,
        database: PostgresDatabase,
        *,
        idle_timeout: timedelta,
        absolute_timeout: timedelta,
    ) -> None:
        self._database = database
        self._idle_timeout = idle_timeout
        self._absolute_timeout = absolute_timeout

    def create(self, principal: AuthenticatedPrincipal) -> IssuedSession:
        now = datetime.now(UTC)
        absolute_expiry = now + self._absolute_timeout
        idle_expiry = min(now + self._idle_timeout, absolute_expiry)
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        with self._database.transaction() as transaction:
            transaction.connection.execute(
                """
                INSERT INTO browser_sessions(
                    token_hash, user_id, csrf_hash, created_at, last_seen_at,
                    idle_expires_at, absolute_expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    token_digest(session_token),
                    principal.user_id,
                    token_digest(csrf_token),
                    now,
                    now,
                    idle_expiry,
                    absolute_expiry,
                ),
            )
            transaction.commit()
        return IssuedSession(session_token, csrf_token, principal, absolute_expiry)

    def resolve(self, session_token: str) -> ActiveSession | None:
        now = datetime.now(UTC)
        digest = token_digest(session_token)
        with self._database.transaction() as transaction:
            row = transaction.connection.execute(
                """
                SELECT s.csrf_hash, s.absolute_expires_at,
                       u.id, u.display_name, u.username, u.role
                FROM browser_sessions AS s
                JOIN users AS u ON u.id = s.user_id
                WHERE s.token_hash=%s AND s.revoked_at IS NULL AND u.is_active
                  AND s.idle_expires_at > %s AND s.absolute_expires_at > %s
                FOR UPDATE OF s
                """,
                (digest, now, now),
            ).fetchone()
            if row is None:
                return None
            absolute_expiry = row["absolute_expires_at"]
            transaction.connection.execute(
                """
                UPDATE browser_sessions
                SET last_seen_at=%s, idle_expires_at=LEAST(%s, absolute_expires_at)
                WHERE token_hash=%s
                """,
                (now, now + self._idle_timeout, digest),
            )
            transaction.commit()
        return ActiveSession(
            token_hash=digest,
            csrf_hash=str(row["csrf_hash"]),
            principal=AuthenticatedPrincipal(
                user_id=int(row["id"]),
                display_name=str(row["display_name"]),
                username=str(row["username"]),
                role=UserRole(str(row["role"])),
            ),
            expires_at=absolute_expiry,
        )

    def revoke(self, session_token: str) -> None:
        with self._database.transaction() as transaction:
            transaction.connection.execute(
                """
                UPDATE browser_sessions SET revoked_at=CURRENT_TIMESTAMP
                WHERE token_hash=%s AND revoked_at IS NULL
                """,
                (token_digest(session_token),),
            )
            transaction.commit()
