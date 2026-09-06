"""Repository and Unit of Work contracts consumed by application services."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import TracebackType
from typing import Protocol, Self

from library_management.domain import (
    Book,
    BookCopy,
    BookCopyStatus,
    BookRequest,
    Feedback,
    FeedbackStatus,
    Fine,
    FineSettlement,
    FineStatus,
    Loan,
    RequestStatus,
    Reservation,
    ReservationStatus,
    User,
    UserRole,
)


class UserRepository(Protocol):
    def add(self, user: User) -> User: ...

    def get_by_id(self, user_id: int) -> User | None: ...

    def get_by_username(self, username: str) -> User | None: ...

    def count_by_role(self, role: UserRole) -> int: ...

    def count_active_by_role(self, role: UserRole) -> int: ...

    def update_password_hash(self, user_id: int, password_hash: str) -> None: ...

    def deactivate(self, user_id: int) -> None: ...


class BookRepository(Protocol):
    def add(self, book: Book) -> Book: ...

    def get_by_id(self, book_id: int) -> Book | None: ...

    def update(self, book: Book) -> None: ...

    def list_all(self) -> list[Book]: ...

    def search(self, query: str) -> list[Book]: ...


class BookCopyRepository(Protocol):
    def add(self, copy: BookCopy) -> BookCopy: ...

    def get_by_id(self, copy_id: int) -> BookCopy | None: ...

    def get_by_barcode(self, barcode: str) -> BookCopy | None: ...

    def list_for_book(self, book_id: int) -> list[BookCopy]: ...

    def update_status(self, copy_id: int, status: BookCopyStatus) -> None: ...


class ReservationRepository(Protocol):
    def add(self, reservation: Reservation) -> Reservation: ...

    def get_by_id(self, reservation_id: int) -> Reservation | None: ...

    def get_active_for_user_book(self, user_id: int, book_id: int) -> Reservation | None: ...

    def list_active_for_book(self, book_id: int) -> list[Reservation]: ...

    def list_for_user(self, user_id: int) -> list[Reservation]: ...

    def resolve(
        self,
        reservation_id: int,
        status: ReservationStatus,
        resolved_at: datetime,
    ) -> None: ...


class LoanRepository(Protocol):
    def add(self, loan: Loan) -> Loan: ...

    def get_by_id(self, loan_id: int) -> Loan | None: ...

    def get_active_by_copy(self, book_copy_id: int) -> Loan | None: ...

    def user_has_active_book(self, user_id: int, book_id: int) -> bool: ...

    def count_active_for_user(self, user_id: int) -> int: ...

    def list_for_user(self, user_id: int) -> list[Loan]: ...

    def mark_returned(self, loan_id: int, returned_at: datetime) -> None: ...

    def renew(self, loan_id: int, due_at: datetime, renewal_count: int) -> None: ...


class FineRepository(Protocol):
    def add(self, fine: Fine) -> Fine: ...

    def get_by_id(self, fine_id: int) -> Fine | None: ...

    def get_by_loan_id(self, loan_id: int) -> Fine | None: ...

    def list_for_user(self, user_id: int) -> list[Fine]: ...

    def settle(self, fine_id: int, status: FineStatus, settled_at: datetime) -> None: ...


class FineSettlementRepository(Protocol):
    def add(self, settlement: FineSettlement) -> FineSettlement: ...

    def get_for_fine(self, fine_id: int) -> FineSettlement | None: ...

    def list_for_user(self, user_id: int) -> list[FineSettlement]: ...


class BookRequestRepository(Protocol):
    def add(self, request: BookRequest) -> BookRequest: ...

    def get_by_id(self, request_id: int) -> BookRequest | None: ...

    def find_pending_duplicate(
        self, user_id: int, title: str, author: str, publication_year: int | None
    ) -> BookRequest | None: ...

    def list_for_user(
        self, user_id: int, status: RequestStatus | None = None
    ) -> list[BookRequest]: ...

    def list_all(self, status: RequestStatus | None = None) -> list[BookRequest]: ...

    def review(
        self,
        request_id: int,
        status: RequestStatus,
        reviewed_by_user_id: int,
        reviewed_at: datetime,
        review_note: str | None,
    ) -> None: ...

    def mark_acquired(
        self,
        request_id: int,
        book_id: int,
        acquired_by_user_id: int,
        acquired_at: datetime,
    ) -> None: ...


class FeedbackRepository(Protocol):
    def add(self, feedback: Feedback) -> Feedback: ...

    def get_by_id(self, feedback_id: int) -> Feedback | None: ...

    def list_for_user(
        self, user_id: int, status: FeedbackStatus | None = None
    ) -> list[Feedback]: ...

    def list_all(self, status: FeedbackStatus | None = None) -> list[Feedback]: ...

    def update_status(
        self,
        feedback_id: int,
        expected_status: FeedbackStatus,
        status: FeedbackStatus,
        reviewed_by_user_id: int,
        reviewed_at: datetime,
    ) -> None: ...


class ReportingRepository(Protocol):
    def count_active_users(self) -> int: ...

    def count_titles(self) -> int: ...

    def count_copies(self) -> tuple[int, int]: ...

    def count_active_loans(self) -> int: ...

    def count_overdue_loans(self, now: datetime) -> int: ...

    def count_active_reservations(self) -> int: ...

    def outstanding_fines(self) -> tuple[int, Decimal]: ...

    def count_pending_requests(self) -> int: ...

    def count_new_feedback(self) -> int: ...

    def loan_counts_by_book(self) -> dict[int, int]: ...


class UnitOfWork(Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def books(self) -> BookRepository: ...

    @property
    def book_copies(self) -> BookCopyRepository: ...

    @property
    def reservations(self) -> ReservationRepository: ...

    @property
    def loans(self) -> LoanRepository: ...

    @property
    def fines(self) -> FineRepository: ...

    @property
    def fine_settlements(self) -> FineSettlementRepository: ...

    @property
    def book_requests(self) -> BookRequestRepository: ...

    @property
    def feedback(self) -> FeedbackRepository: ...

    @property
    def reporting(self) -> ReportingRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def lock_bootstrap(self) -> None: ...

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
    ) -> None: ...
