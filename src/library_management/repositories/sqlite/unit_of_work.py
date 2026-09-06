"""SQLite Unit of Work implementation."""

from __future__ import annotations

import sqlite3
from types import TracebackType

from library_management.database import Database
from library_management.repositories.sqlite.books import (
    SqliteBookCopyRepository,
    SqliteBookRepository,
)
from library_management.repositories.sqlite.circulation import (
    SqliteLoanRepository,
    SqliteReservationRepository,
)
from library_management.repositories.sqlite.engagement import (
    SqliteBookRequestRepository,
    SqliteFeedbackRepository,
)
from library_management.repositories.sqlite.financial import (
    SqliteFineRepository,
    SqliteFineSettlementRepository,
)
from library_management.repositories.sqlite.reporting import SqliteReportingRepository
from library_management.repositories.sqlite.users import SqliteUserRepository


class SqliteUnitOfWork:
    """Own one SQLite transaction spanning all exposed repositories."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._connection: sqlite3.Connection | None = None
        self._committed = False

    @property
    def users(self) -> SqliteUserRepository:
        return SqliteUserRepository(self._active_connection())

    @property
    def books(self) -> SqliteBookRepository:
        return SqliteBookRepository(self._active_connection())

    @property
    def book_copies(self) -> SqliteBookCopyRepository:
        return SqliteBookCopyRepository(self._active_connection())

    @property
    def reservations(self) -> SqliteReservationRepository:
        return SqliteReservationRepository(self._active_connection())

    @property
    def loans(self) -> SqliteLoanRepository:
        return SqliteLoanRepository(self._active_connection())

    @property
    def fines(self) -> SqliteFineRepository:
        return SqliteFineRepository(self._active_connection())

    @property
    def fine_settlements(self) -> SqliteFineSettlementRepository:
        return SqliteFineSettlementRepository(self._active_connection())

    @property
    def book_requests(self) -> SqliteBookRequestRepository:
        return SqliteBookRequestRepository(self._active_connection())

    @property
    def feedback(self) -> SqliteFeedbackRepository:
        return SqliteFeedbackRepository(self._active_connection())

    @property
    def reporting(self) -> SqliteReportingRepository:
        return SqliteReportingRepository(self._active_connection())

    def __enter__(self) -> SqliteUnitOfWork:
        if self._connection is not None:
            raise RuntimeError("This Unit of Work is already active.")
        self._connection = self._database.connect()
        self._connection.execute("BEGIN")
        self._committed = False
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback
        if self._connection is None:
            return
        try:
            if not self._committed:
                self._connection.rollback()
        finally:
            self._connection.close()
            self._connection = None

    def commit(self) -> None:
        connection = self._active_connection()
        connection.commit()
        self._committed = True

    def rollback(self) -> None:
        connection = self._active_connection()
        connection.rollback()
        self._committed = False

    def lock_bootstrap(self) -> None:
        """SQLite serializes the transitional CLI's single-process writes."""

    def lock_rows(
        self,
        *,
        users: tuple[int, ...] = (),
        books: tuple[int, ...] = (),
        book_copies: tuple[int, ...] = (),
        reservations: tuple[int, ...] = (),
        loans: tuple[int, ...] = (),
        fines: tuple[int, ...] = (),
        book_requests: tuple[int, ...] = (),
        feedback: tuple[int, ...] = (),
    ) -> None:
        """Row locks are a PostgreSQL concern; retain the shared service contract."""
        del users, books, book_copies, reservations, loans, fines, book_requests, feedback

    def _active_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("The Unit of Work must be entered before use.")
        return self._connection
