"""Browser security and service routing against disposable PostgreSQL."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from library_management.api import create_app
from library_management.api.config import ApiSettings, Environment
from library_management.domain import User, UserRole
from library_management.postgres import PostgresDatabase
from library_management.repositories.postgres import PostgresUnitOfWork
from library_management.security import PasswordService

pytestmark = pytest.mark.postgres
ORIGIN = "http://localhost:3000"
PASSWORD = "correct horse battery staple"


def test_login_session_csrf_idempotency_and_logout(
    pg_url: str, pg_database: PostgresDatabase
) -> None:
    librarian = _seed_user(pg_database, UserRole.LIBRARIAN)
    settings = _settings(pg_url)
    with TestClient(create_app(settings)) as client:
        unauthenticated = client.get("/api/v1/catalog/books")
        assert unauthenticated.status_code == 401
        assert unauthenticated.json()["code"] == "authentication_required"

        bad_login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": librarian.username, "password": "incorrect"},
        )
        assert bad_login.status_code == 401
        assert bad_login.json()["code"] == "invalid_credentials"

        login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": librarian.username, "password": PASSWORD},
        )
        assert login.status_code == 200
        csrf = login.json()["csrf_token"]
        assert "httponly" in login.headers.get_list("set-cookie")[0].lower()
        assert PASSWORD not in " ".join(login.headers.get_list("set-cookie"))

        missing_csrf = client.post(
            "/api/v1/catalog/books",
            headers={"Origin": ORIGIN, "Idempotency-Key": "catalog-no-csrf"},
            json=_book_payload("No CSRF"),
        )
        assert missing_csrf.status_code == 403

        headers = {
            "Origin": ORIGIN,
            "X-CSRF-Token": csrf,
            "Idempotency-Key": "catalog-create-0001",
        }
        created = client.post(
            "/api/v1/catalog/books",
            headers=headers,
            json=_book_payload("Atomic HTTP"),
        )
        replay = client.post(
            "/api/v1/catalog/books",
            headers=headers,
            json=_book_payload("Atomic HTTP"),
        )
        conflict = client.post(
            "/api/v1/catalog/books",
            headers=headers,
            json=_book_payload("Different request"),
        )
        assert created.status_code == replay.status_code == 201
        assert replay.json() == created.json()
        assert created.headers["idempotency-replayed"] == "false"
        assert replay.headers["idempotency-replayed"] == "true"
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "idempotency_conflict"

        books = client.get("/api/v1/catalog/books", params={"limit": 1})
        assert books.status_code == 200
        assert len(books.json()) == 1

        logout = client.post(
            "/api/v1/auth/logout",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        )
        assert logout.status_code == 204
        assert client.get("/api/v1/auth/session").status_code == 401

    with pg_database.transaction() as transaction:
        rows = transaction.connection.execute(
            "SELECT token_hash, csrf_hash, revoked_at FROM browser_sessions WHERE user_id=%s",
            (librarian.id,),
        ).fetchall()
    assert rows and rows[-1]["revoked_at"] is not None
    assert len(rows[-1]["token_hash"]) == len(rows[-1]["csrf_hash"]) == 64
    assert csrf not in {rows[-1]["token_hash"], rows[-1]["csrf_hash"]}


def test_origin_throttle_and_account_deactivation_revoke_session(
    pg_url: str, pg_database: PostgresDatabase
) -> None:
    member = _seed_user(pg_database, UserRole.MEMBER)
    settings = _settings(pg_url, login_rate_limit=1)
    with TestClient(create_app(settings)) as client:
        rejected_origin = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://untrusted.example"},
            json={"username": member.username, "password": PASSWORD},
        )
        assert rejected_origin.status_code == 403
        assert rejected_origin.json()["code"] == "origin_rejected"

        first = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": member.username, "password": "wrong"},
        )
        limited = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": member.username, "password": PASSWORD},
        )
        assert first.status_code == 401
        assert limited.status_code == 429
        assert int(limited.headers["retry-after"]) >= 1

    with TestClient(create_app(_settings(pg_url))) as client:
        login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": member.username, "password": PASSWORD},
        )
        assert login.status_code == 200
        with pg_database.transaction() as transaction:
            transaction.connection.execute(
                "UPDATE users SET is_active=false WHERE id=%s", (member.id,)
            )
            transaction.commit()
        assert client.get("/api/v1/auth/session").status_code == 401
        with pg_database.transaction() as transaction:
            row = transaction.connection.execute(
                "SELECT revoked_at FROM browser_sessions WHERE user_id=%s", (member.id,)
            ).fetchone()
        assert row is not None and row["revoked_at"] is not None


def test_idle_expired_session_is_rejected(pg_url: str, pg_database: PostgresDatabase) -> None:
    member = _seed_user(pg_database, UserRole.MEMBER)
    with TestClient(create_app(_settings(pg_url))) as client:
        login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": member.username, "password": PASSWORD},
        )
        assert login.status_code == 200
        with pg_database.transaction() as transaction:
            transaction.connection.execute(
                """
                UPDATE browser_sessions
                SET idle_expires_at=created_at + interval '1 microsecond'
                WHERE user_id=%s
                """,
                (member.id,),
            )
            transaction.commit()

        expired = client.get("/api/v1/auth/session")

    assert expired.status_code == 401
    assert expired.json()["code"] == "authentication_required"


def _seed_user(database: PostgresDatabase, role: UserRole) -> User:
    user = User(
        display_name=f"{role.value.title()} Test",
        username=f"{role.value}.{uuid4().hex[:12]}",
        password_hash=PasswordService().hash(PASSWORD),
        role=role,
    )
    with PostgresUnitOfWork(database) as unit:
        saved = unit.users.add(user)
        unit.commit()
    return saved


def _settings(pg_url: str, *, login_rate_limit: int = 5) -> ApiSettings:
    return ApiSettings(
        environment=Environment.TEST,
        allowed_origins=(ORIGIN,),
        database_url=pg_url,
        login_rate_limit=login_rate_limit,
    )


def _book_payload(title: str) -> dict[str, object]:
    return {"title": title, "author": "Plan 16", "publication_year": 2026}
