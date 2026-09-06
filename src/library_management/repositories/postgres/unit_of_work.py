"""Business Unit of Work over one PostgreSQL transaction."""

from __future__ import annotations

from types import TracebackType

from library_management.postgres.database import PostgresDatabase, PostgresTransaction
from library_management.repositories.postgres.books import (
    PostgresBookCopyRepository,
    PostgresBookRepository,
)
from library_management.repositories.postgres.circulation import (
    PostgresLoanRepository,
    PostgresReservationRepository,
)
from library_management.repositories.postgres.engagement import (
    PostgresBookRequestRepository,
    PostgresFeedbackRepository,
)
from library_management.repositories.postgres.financial import (
    PostgresFineRepository,
    PostgresFineSettlementRepository,
)
from library_management.repositories.postgres.idempotency import (
    PostgresIdempotencyRepository,
)
from library_management.repositories.postgres.reporting import PostgresReportingRepository
from library_management.repositories.postgres.users import PostgresUserRepository


class PostgresUnitOfWork:
    """Expose all repositories on one connection and one explicit transaction."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database
        self._transaction: PostgresTransaction | None = None

    @property
    def users(self) -> PostgresUserRepository:
        return PostgresUserRepository(self._active_transaction().connection)

    @property
    def books(self) -> PostgresBookRepository:
        return PostgresBookRepository(self._active_transaction().connection)

    @property
    def book_copies(self) -> PostgresBookCopyRepository:
        return PostgresBookCopyRepository(self._active_transaction().connection)

    @property
    def reservations(self) -> PostgresReservationRepository:
        return PostgresReservationRepository(self._active_transaction().connection)

    @property
    def loans(self) -> PostgresLoanRepository:
        return PostgresLoanRepository(self._active_transaction().connection)

    @property
    def fines(self) -> PostgresFineRepository:
        return PostgresFineRepository(self._active_transaction().connection)

    @property
    def fine_settlements(self) -> PostgresFineSettlementRepository:
        return PostgresFineSettlementRepository(self._active_transaction().connection)

    @property
    def book_requests(self) -> PostgresBookRequestRepository:
        return PostgresBookRequestRepository(self._active_transaction().connection)

    @property
    def feedback(self) -> PostgresFeedbackRepository:
        return PostgresFeedbackRepository(self._active_transaction().connection)

    @property
    def reporting(self) -> PostgresReportingRepository:
        return PostgresReportingRepository(self._active_transaction().connection)

    @property
    def idempotency(self) -> PostgresIdempotencyRepository:
        return PostgresIdempotencyRepository(self._active_transaction().connection)

    def __enter__(self) -> PostgresUnitOfWork:
        if self._transaction is not None:
            raise RuntimeError("This Unit of Work is already active.")
        transaction = self._database.transaction()
        transaction.__enter__()
        self._transaction = transaction
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        transaction, self._transaction = self._transaction, None
        if transaction is not None:
            transaction.__exit__(exception_type, exception, traceback)

    def commit(self) -> None:
        self._active_transaction().commit()

    def rollback(self) -> None:
        self._active_transaction().rollback()

    def borrowed(self) -> BorrowedPostgresUnitOfWork:
        """Lend this transaction to one service without allowing an early commit."""
        self._active_transaction()
        return BorrowedPostgresUnitOfWork(self)

    def lock_bootstrap(self) -> None:
        self._active_transaction().connection.execute(
            "SELECT pg_advisory_xact_lock(1279873875, 100)"
        )

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
        """Lock requested aggregates in the project's canonical table/id order."""
        connection = self._active_transaction().connection
        for statement, identifiers in (
            ("SELECT id FROM users WHERE id=ANY(%s) ORDER BY id FOR UPDATE", users),
            ("SELECT id FROM books WHERE id=ANY(%s) ORDER BY id FOR UPDATE", books),
            (
                "SELECT id FROM book_copies WHERE id=ANY(%s) ORDER BY id FOR UPDATE",
                book_copies,
            ),
            (
                "SELECT id FROM reservations WHERE id=ANY(%s) ORDER BY id FOR UPDATE",
                reservations,
            ),
            ("SELECT id FROM loans WHERE id=ANY(%s) ORDER BY id FOR UPDATE", loans),
            ("SELECT id FROM fines WHERE id=ANY(%s) ORDER BY id FOR UPDATE", fines),
            (
                "SELECT id FROM book_requests WHERE id=ANY(%s) ORDER BY id FOR UPDATE",
                book_requests,
            ),
            ("SELECT id FROM feedback WHERE id=ANY(%s) ORDER BY id FOR UPDATE", feedback),
        ):
            ordered = sorted(set(identifiers))
            if ordered:
                connection.execute(statement, (ordered,)).fetchall()

    def _active_transaction(self) -> PostgresTransaction:
        if self._transaction is None:
            raise RuntimeError("The Unit of Work must be entered before use.")
        return self._transaction


class BorrowedPostgresUnitOfWork:
    """Service-facing view used by atomic HTTP idempotency execution."""

    def __init__(self, owner: PostgresUnitOfWork) -> None:
        self._owner = owner

    def __enter__(self) -> BorrowedPostgresUnitOfWork:
        self._owner._active_transaction()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    @property
    def users(self) -> PostgresUserRepository:
        return self._owner.users

    @property
    def books(self) -> PostgresBookRepository:
        return self._owner.books

    @property
    def book_copies(self) -> PostgresBookCopyRepository:
        return self._owner.book_copies

    @property
    def reservations(self) -> PostgresReservationRepository:
        return self._owner.reservations

    @property
    def loans(self) -> PostgresLoanRepository:
        return self._owner.loans

    @property
    def fines(self) -> PostgresFineRepository:
        return self._owner.fines

    @property
    def fine_settlements(self) -> PostgresFineSettlementRepository:
        return self._owner.fine_settlements

    @property
    def book_requests(self) -> PostgresBookRequestRepository:
        return self._owner.book_requests

    @property
    def feedback(self) -> PostgresFeedbackRepository:
        return self._owner.feedback

    @property
    def reporting(self) -> PostgresReportingRepository:
        return self._owner.reporting

    def commit(self) -> None:
        """The outer HTTP command owns the only real commit."""

    def rollback(self) -> None:
        self._owner.rollback()

    def lock_bootstrap(self) -> None:
        self._owner.lock_bootstrap()

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
        self._owner.lock_rows(
            users=users,
            books=books,
            book_copies=book_copies,
            reservations=reservations,
            loans=loans,
            fines=fines,
            book_requests=book_requests,
            feedback=feedback,
        )
