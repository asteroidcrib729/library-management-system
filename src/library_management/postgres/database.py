"""Synchronous pool lifecycle, explicit transactions and bounded whole-command retries."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from types import TracebackType
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolClosed, PoolTimeout, TooManyRequests

from library_management.postgres.config import PostgresSettings
from library_management.repositories.errors import (
    DuplicateRecordError,
    PersistenceError,
    RecordNotFoundError,
)

SCHEMA_VERSION = 3
logger = logging.getLogger(__name__)
type Row = dict[str, Any]


class DatabaseUnavailableError(PersistenceError):
    """Database connection or pool is unavailable; outcome may be ambiguous."""


class TransactionBusyError(PersistenceError):
    """The operation exceeded a bounded pool/query/lock wait."""


class RetryableTransactionError(TransactionBusyError):
    """PostgreSQL aborted the transaction for deadlock or serialization conflict."""


def _translate(error: BaseException) -> None:
    if isinstance(error, psycopg.errors.UniqueViolation):
        raise DuplicateRecordError("A unique database record already exists.") from None
    if isinstance(error, psycopg.errors.ForeignKeyViolation):
        raise RecordNotFoundError("A referenced database record was not found.") from None
    if isinstance(error, (psycopg.errors.CheckViolation, psycopg.errors.NotNullViolation)):
        raise PersistenceError("The database rejected an invalid record state.") from None
    if isinstance(error, (psycopg.errors.DeadlockDetected, psycopg.errors.SerializationFailure)):
        raise RetryableTransactionError(
            "Transaction conflicted; retry the complete command."
        ) from None
    if isinstance(
        error,
        (
            PoolTimeout,
            TooManyRequests,
            psycopg.errors.LockNotAvailable,
            psycopg.errors.QueryCanceled,
        ),
    ):
        raise TransactionBusyError("Database is busy; retry later.") from None
    if isinstance(error, (PoolClosed, psycopg.OperationalError)):
        raise DatabaseUnavailableError("Database is unavailable.") from None


class PostgresDatabase:
    """One closed-on-construction pool per process; no startup schema mutation."""

    def __init__(self, settings: PostgresSettings) -> None:
        self.settings = settings
        self.pool: ConnectionPool[Connection[Row]] = ConnectionPool(
            settings.url,
            kwargs={
                "row_factory": dict_row,
                "connect_timeout": 3,
                "application_name": "lms-api",
                "options": "-c timezone=UTC -c search_path=lms,pg_catalog",
            },
            min_size=0,
            max_size=settings.max_size,
            max_waiting=settings.max_waiting,
            timeout=settings.acquire_timeout,
            check=ConnectionPool.check_connection,
            open=False,
            name="lms",
            reconnect_timeout=10,
        )

    def open(self) -> None:
        self.pool.open(wait=False)

    def close(self) -> None:
        self.pool.close()

    def transaction(self) -> PostgresTransaction:
        return PostgresTransaction(self)

    def schema_ready(self) -> bool:
        """An explicit connection check is necessary even with min_size=0."""
        try:
            with self.transaction() as transaction:
                rows = transaction.connection.execute(
                    "SELECT version FROM lms.schema_version ORDER BY version"
                ).fetchall()
                return [row["version"] for row in rows] == list(range(1, SCHEMA_VERSION + 1))
        except psycopg.Error, PersistenceError:
            return False

    def run[T](self, operation: Callable[[PostgresTransaction], T]) -> T:
        """Run a database-only callback; commit once and retry confirmed aborts only."""
        for attempt in range(3):
            try:
                with self.transaction() as transaction:
                    result = operation(transaction)
                    transaction.commit()
                    return result
            except RetryableTransactionError:
                if attempt == 2:
                    raise
                logger.warning("postgres_transaction_retry attempt=%s", attempt + 1)
                time.sleep(0.02 * 2**attempt + random.uniform(0, 0.02))
        raise AssertionError("Unreachable retry state.")


class PostgresTransaction:
    """Own exactly one checked-out connection, committing only on explicit request.

    This is the infrastructure primitive, not yet the business UnitOfWork protocol.
    Plan 14 composes repositories on its connection and defines aggregate lock order.
    """

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database
        self._connection: Connection[Row] | None = None
        self._finished = False
        self._started = 0.0

    @property
    def connection(self) -> Connection[Row]:
        if self._connection is None or self._finished:
            raise RuntimeError("Transaction must be active and not already completed.")
        return self._connection

    def __enter__(self) -> PostgresTransaction:
        if self._connection is not None:
            raise RuntimeError("Transaction is already active.")
        self._finished = False
        self._started = time.monotonic()
        try:
            self._connection = self._database.pool.getconn()
            self.connection.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            settings = self._database.settings
            self.connection.execute(
                "SELECT set_config('lock_timeout', %s, true), "
                "set_config('statement_timeout', %s, true), "
                "set_config('idle_in_transaction_session_timeout', %s, true)",
                (
                    str(settings.lock_timeout_ms),
                    str(settings.statement_timeout_ms),
                    str(settings.idle_transaction_timeout_ms),
                ),
            )
        except BaseException as error:
            self._release()
            _translate(error)
            raise
        return self

    def commit(self) -> None:
        self.connection.commit()
        self._finished = True

    def rollback(self) -> None:
        self.connection.rollback()
        self._finished = True

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._release()
        logger.debug(
            "postgres_transaction duration_ms=%.2f", (time.monotonic() - self._started) * 1000
        )
        if exception is not None:
            _translate(exception)

    def _release(self) -> None:
        connection, self._connection = self._connection, None
        if connection is None:
            return
        try:
            connection.rollback()
        except psycopg.Error:
            connection.close()
        finally:
            self._database.pool.putconn(connection)
