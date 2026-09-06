"""Atomic PostgreSQL idempotency claims for future HTTP command handlers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb

from library_management.postgres.database import Row
from library_management.repositories.errors import PersistenceError

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class IdempotencyDecision(StrEnum):
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    REPLAY = "replay"


class IdempotencyConflictError(PersistenceError):
    """The key was reused with another request or completed by a stale owner."""


@dataclass(frozen=True, slots=True)
class IdempotencyResult:
    decision: IdempotencyDecision
    response: dict[str, Any] | None = None
    response_status: int | None = None


class PostgresIdempotencyRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def claim(
        self,
        *,
        actor_id: int,
        operation: str,
        key: str,
        request_hash: str,
        owner_token: str,
        now: datetime,
        expires_at: datetime,
    ) -> IdempotencyResult:
        if not SHA256_PATTERN.fullmatch(request_hash):
            raise ValueError("Request hash must be a lowercase SHA-256 digest.")
        if not operation or not key or not owner_token:
            raise ValueError("Operation, key, and owner token are required.")
        inserted = self._connection.execute(
            """
            INSERT INTO idempotency_records(
                actor_id, operation, key, request_hash, expires_at, state, owner_token)
            VALUES (%s, %s, %s, %s, %s, 'processing', %s)
            ON CONFLICT (actor_id, operation, key) DO NOTHING
            RETURNING actor_id
            """,
            (actor_id, operation, key, request_hash, expires_at, owner_token),
        ).fetchone()
        if inserted is not None:
            return IdempotencyResult(IdempotencyDecision.CLAIMED)

        row = self._connection.execute(
            """
            SELECT request_hash, response, response_status, state, expires_at
            FROM idempotency_records
            WHERE actor_id=%s AND operation=%s AND key=%s
            FOR UPDATE
            """,
            (actor_id, operation, key),
        ).fetchone()
        if row is None:
            raise RuntimeError("The conflicting idempotency record disappeared.")
        if row["request_hash"] != request_hash:
            raise IdempotencyConflictError(
                "This idempotency key was already used for a different request."
            )
        if row["state"] == "completed":
            response = row["response"]
            if not isinstance(response, dict) or row["response_status"] is None:
                raise RuntimeError("Completed idempotency response is invalid.")
            return IdempotencyResult(
                IdempotencyDecision.REPLAY,
                response,
                int(row["response_status"]),
            )
        expiry = row["expires_at"]
        if not isinstance(expiry, datetime):
            raise RuntimeError("Idempotency expiry is invalid.")
        if expiry > now:
            return IdempotencyResult(IdempotencyDecision.IN_PROGRESS)
        self._connection.execute(
            """
            UPDATE idempotency_records
            SET owner_token=%s, expires_at=%s
            WHERE actor_id=%s AND operation=%s AND key=%s AND state='processing'
            """,
            (owner_token, expires_at, actor_id, operation, key),
        )
        return IdempotencyResult(IdempotencyDecision.CLAIMED)

    def complete(
        self,
        *,
        actor_id: int,
        operation: str,
        key: str,
        owner_token: str,
        response: dict[str, Any],
        response_status: int,
        expires_at: datetime | None = None,
    ) -> None:
        if not 200 <= response_status <= 499:
            raise ValueError("Response status must be between 200 and 499.")
        cursor = self._connection.execute(
            """
            UPDATE idempotency_records
            SET state='completed', owner_token=NULL, response=%s, response_status=%s,
                expires_at=COALESCE(%s, expires_at)
            WHERE actor_id=%s AND operation=%s AND key=%s
              AND state='processing' AND owner_token=%s
            """,
            (
                Jsonb(response),
                response_status,
                expires_at,
                actor_id,
                operation,
                key,
                owner_token,
            ),
        )
        if cursor.rowcount == 0:
            raise IdempotencyConflictError(
                "The idempotency claim is missing, completed, or owned by another request."
            )
