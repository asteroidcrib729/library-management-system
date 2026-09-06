"""Bounded pool configuration and explicit database environment identity."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True, slots=True)
class PostgresSettings:
    url: str = field(repr=False)
    environment: str = "local"
    max_size: int = 5
    max_waiting: int = 10
    acquire_timeout: float = 2.0
    lock_timeout_ms: int = 2000
    statement_timeout_ms: int = 5000
    idle_transaction_timeout_ms: int = 10000

    def __post_init__(self) -> None:
        try:
            parsed = urlsplit(self.url)
            port = parsed.port
        except ValueError:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL.") from None
        if self.environment not in {"local", "test", "preview", "staging", "production"}:
            raise ValueError("Unknown PostgreSQL environment.")
        if (
            parsed.scheme not in {"postgres", "postgresql"}
            or not parsed.hostname
            or not parsed.username
            or not parsed.path.strip("/")
            or parsed.fragment
            or port == 0
        ):
            raise ValueError("DATABASE_URL requires a PostgreSQL host, user and database.")
        query = parse_qs(parsed.query, keep_blank_values=True)
        if set(query) - {"sslmode"} or any(len(values) != 1 for values in query.values()):
            raise ValueError("Only one sslmode query parameter is supported in DATABASE_URL.")
        if self.environment in {"local", "test"}:
            if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Local/test PostgreSQL must use a loopback host.")
        elif query.get("sslmode") not in (["require"], ["verify-ca"], ["verify-full"]):
            raise ValueError("Hosted PostgreSQL requires sslmode=require or stronger.")
        if not 1 <= self.max_size <= 20 or not 1 <= self.max_waiting <= 100:
            raise ValueError("Pool maximum must be 1-20 and queue maximum 1-100.")
        if not 0 < self.acquire_timeout <= 10:
            raise ValueError("Pool acquisition timeout must be above zero and at most 10 seconds.")
        if not 1 <= self.lock_timeout_ms <= self.statement_timeout_ms <= 30000:
            raise ValueError("Timeouts require 1 <= lock <= statement <= 30000 milliseconds.")
        if not self.statement_timeout_ms <= self.idle_transaction_timeout_ms <= 60000:
            raise ValueError(
                "Idle transaction timeout must be between statement timeout and 60000."
            )

    @classmethod
    def from_environment(cls, url: str, environment: str) -> PostgresSettings:
        try:
            return cls(
                url=url,
                environment=environment,
                max_size=int(os.environ.get("LMS_DB_POOL_MAX", "5")),
                max_waiting=int(os.environ.get("LMS_DB_POOL_MAX_WAITING", "10")),
                acquire_timeout=float(os.environ.get("LMS_DB_ACQUIRE_TIMEOUT", "2")),
                lock_timeout_ms=int(os.environ.get("LMS_DB_LOCK_TIMEOUT_MS", "2000")),
                statement_timeout_ms=int(os.environ.get("LMS_DB_STATEMENT_TIMEOUT_MS", "5000")),
                idle_transaction_timeout_ms=int(os.environ.get("LMS_DB_IDLE_TIMEOUT_MS", "10000")),
            )
        except ValueError:
            raise ValueError("Invalid PostgreSQL URL or LMS_DB_* configuration.") from None
