"""Reservation queues and transactional loan-circulation use cases."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from library_management.domain import (
    Book,
    BookCopy,
    BookCopyStatus,
    Fine,
    Loan,
    Reservation,
    ReservationStatus,
    User,
    UserRole,
)
from library_management.repositories import DuplicateRecordError, UnitOfWork
from library_management.services.accounts import UnitOfWorkFactory
from library_management.services.authorization import require_active_user, require_role
from library_management.services.errors import (
    AuthorizationError,
    CirculationNotFoundError,
    CopyUnavailableError,
    LoanLimitError,
    RenewalNotAllowedError,
    ReservationConflictError,
    ReservationQueueError,
)
from library_management.services.financial import FinePolicy

Clock = Callable[[], datetime]
CIRCULATION_STAFF_ROLES = frozenset({UserRole.LIBRARIAN, UserRole.ADMINISTRATOR})
RESERVABLE_COPY_STATUSES = frozenset(
    {BookCopyStatus.AVAILABLE, BookCopyStatus.ON_LOAN, BookCopyStatus.DAMAGED}
)


def system_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CirculationPolicy:
    loan_period: timedelta = timedelta(days=14)
    maximum_active_loans: int = 5
    maximum_renewals: int = 2

    def __post_init__(self) -> None:
        if self.loan_period <= timedelta(0):
            raise ValueError("Loan period must be positive.")
        if self.maximum_active_loans <= 0:
            raise ValueError("Maximum active loans must be positive.")
        if self.maximum_renewals < 0:
            raise ValueError("Maximum renewals cannot be negative.")


@dataclass(frozen=True, slots=True)
class ReservationView:
    reservation: Reservation
    book_title: str
    queue_position: int | None


@dataclass(frozen=True, slots=True)
class LoanView:
    loan: Loan
    book: Book
    copy: BookCopy
    borrower_username: str
    is_overdue: bool
    assessed_fine: Fine | None = None


class CirculationService:
    """Enforce reservation and loan policies within atomic Units of Work."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        policy: CirculationPolicy | None = None,
        fine_policy: FinePolicy | None = None,
        clock: Clock = system_clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._policy = policy or CirculationPolicy()
        self._fine_policy = fine_policy or FinePolicy()
        self._clock = clock

    def reserve(self, actor_id: int, book_id: int) -> ReservationView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.lock_rows(users=(actor_id,), books=(book_id,))
            require_active_user(unit_of_work, actor_id)
            book = self._get_book(unit_of_work, book_id)
            copies = unit_of_work.book_copies.list_for_book(book_id)
            if not any(copy.status in RESERVABLE_COPY_STATUSES for copy in copies):
                raise ReservationConflictError("This book has no reservable physical copies.")
            if unit_of_work.loans.user_has_active_book(actor_id, book_id):
                raise ReservationConflictError(
                    "You cannot reserve a book that is already on loan to your account."
                )
            reservation = Reservation(user_id=actor_id, book_id=book_id, created_at=now)
            try:
                saved = unit_of_work.reservations.add(reservation)
            except DuplicateRecordError as error:
                raise ReservationConflictError(
                    "You already have an active reservation for this book."
                ) from error
            queue = unit_of_work.reservations.list_active_for_book(book_id)
            position = self._queue_position(queue, saved.id)
            unit_of_work.commit()
        return ReservationView(saved, book.title, position)

    def list_reservations(self, actor_id: int) -> list[ReservationView]:
        with self._unit_of_work_factory() as unit_of_work:
            require_active_user(unit_of_work, actor_id)
            reservations = unit_of_work.reservations.list_for_user(actor_id)
            return [self._reservation_view(unit_of_work, item) for item in reservations]

    def cancel_reservation(self, actor_id: int, reservation_id: int) -> ReservationView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            reservation = unit_of_work.reservations.get_by_id(reservation_id)
            if reservation is None:
                raise CirculationNotFoundError(f"Reservation {reservation_id} was not found.")
            unit_of_work.lock_rows(
                users=(actor_id, reservation.user_id),
                books=(reservation.book_id,),
                reservations=(reservation_id,),
            )
            actor = require_active_user(unit_of_work, actor_id)
            reservation = unit_of_work.reservations.get_by_id(reservation_id)
            if reservation is None:
                raise CirculationNotFoundError(f"Reservation {reservation_id} was not found.")
            if reservation.status is not ReservationStatus.ACTIVE:
                raise ReservationConflictError("Only an active reservation can be cancelled.")
            if actor.id != reservation.user_id and actor.role not in CIRCULATION_STAFF_ROLES:
                raise AuthorizationError("You may only cancel your own reservations.")
            book = self._get_book(unit_of_work, reservation.book_id)
            if reservation.id is None:
                raise RuntimeError("A stored reservation is missing its identifier.")
            unit_of_work.reservations.resolve(reservation.id, ReservationStatus.CANCELLED, now)
            unit_of_work.commit()
        cancelled = replace(
            reservation,
            status=ReservationStatus.CANCELLED,
            resolved_at=now,
        )
        return ReservationView(cancelled, book.title, None)

    def checkout(self, actor_id: int, borrower_username: str, barcode: str) -> LoanView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            self._require_circulation_staff(unit_of_work, actor_id)
            borrower = unit_of_work.users.get_by_username(borrower_username)
            if borrower is None or not borrower.is_active or borrower.id is None:
                raise CirculationNotFoundError("An active borrower account was not found.")
            copy = unit_of_work.book_copies.get_by_barcode(barcode)
            if copy is None or copy.id is None:
                raise CirculationNotFoundError(f"Book copy '{barcode.strip()}' was not found.")
            unit_of_work.lock_rows(
                users=(actor_id, borrower.id),
                books=(copy.book_id,),
                book_copies=(copy.id,),
            )
            self._require_circulation_staff(unit_of_work, actor_id)
            borrower = unit_of_work.users.get_by_id(borrower.id)
            copy = unit_of_work.book_copies.get_by_id(copy.id)
            if borrower is None or not borrower.is_active or borrower.id is None:
                raise CirculationNotFoundError("An active borrower account was not found.")
            if copy is None or copy.id is None:
                raise CirculationNotFoundError(f"Book copy '{barcode.strip()}' was not found.")
            if copy.status is not BookCopyStatus.AVAILABLE:
                raise CopyUnavailableError(
                    f"Book copy '{copy.barcode}' is not available for checkout."
                )
            book = self._get_book(unit_of_work, copy.book_id)
            if unit_of_work.loans.user_has_active_book(borrower.id, copy.book_id):
                raise CopyUnavailableError("The borrower already has this book on active loan.")
            if (
                unit_of_work.loans.count_active_for_user(borrower.id)
                >= self._policy.maximum_active_loans
            ):
                raise LoanLimitError("The borrower has reached the active-loan limit.")

            queue = unit_of_work.reservations.list_active_for_book(copy.book_id)
            reservation = queue[0] if queue else None
            if reservation is not None and reservation.user_id != borrower.id:
                raise ReservationQueueError(
                    "This book is reserved for the first account in its queue."
                )

            loan = Loan(
                user_id=borrower.id,
                book_copy_id=copy.id,
                checked_out_at=now,
                due_at=now + self._policy.loan_period,
            )
            try:
                saved = unit_of_work.loans.add(loan)
            except DuplicateRecordError as error:
                raise CopyUnavailableError("The copy already has an active loan.") from error
            unit_of_work.book_copies.update_status(copy.id, BookCopyStatus.ON_LOAN)
            if reservation is not None:
                if reservation.id is None:
                    raise RuntimeError("A stored reservation is missing its identifier.")
                unit_of_work.reservations.resolve(reservation.id, ReservationStatus.FULFILLED, now)
            unit_of_work.commit()

        return LoanView(
            loan=saved,
            book=book,
            copy=replace(copy, status=BookCopyStatus.ON_LOAN),
            borrower_username=borrower.username,
            is_overdue=False,
        )

    def return_copy(self, actor_id: int, barcode: str) -> LoanView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            self._require_circulation_staff(unit_of_work, actor_id)
            copy = unit_of_work.book_copies.get_by_barcode(barcode)
            if copy is None or copy.id is None:
                raise CirculationNotFoundError(f"Book copy '{barcode.strip()}' was not found.")
            loan = unit_of_work.loans.get_active_by_copy(copy.id)
            if loan is None or loan.id is None:
                raise CopyUnavailableError("This copy has no active loan to return.")
            unit_of_work.lock_rows(
                users=(actor_id, loan.user_id),
                books=(copy.book_id,),
                book_copies=(copy.id,),
                loans=(loan.id,),
            )
            self._require_circulation_staff(unit_of_work, actor_id)
            copy = unit_of_work.book_copies.get_by_id(copy.id)
            loan = unit_of_work.loans.get_by_id(loan.id)
            if copy is None or copy.id is None or loan is None or loan.id is None:
                raise CopyUnavailableError("This copy has no active loan to return.")
            if loan.returned_at is not None:
                raise CopyUnavailableError("This copy has no active loan to return.")
            book = self._get_book(unit_of_work, copy.book_id)
            borrower = self._get_user(unit_of_work, loan.user_id)
            unit_of_work.loans.mark_returned(loan.id, now)
            unit_of_work.book_copies.update_status(copy.id, BookCopyStatus.AVAILABLE)
            overdue_days = self._fine_policy.overdue_days(loan.due_at, now)
            assessed_fine = None
            if overdue_days:
                amount = self._fine_policy.overdue_amount(loan.due_at, now)
                assessed_fine = unit_of_work.fines.add(
                    Fine(
                        user_id=borrower.id or loan.user_id,
                        loan_id=loan.id,
                        reason=(
                            f"Overdue return: {overdue_days} started day(s) at "
                            f"{self._fine_policy.currency_code} "
                            f"{self._fine_policy.daily_overdue_rate:.2f} per day."
                        ),
                        amount=amount,
                        assessed_at=now,
                    )
                )
            unit_of_work.commit()

        returned_loan = replace(loan, returned_at=now)
        return LoanView(
            loan=returned_loan,
            book=book,
            copy=replace(copy, status=BookCopyStatus.AVAILABLE),
            borrower_username=borrower.username,
            is_overdue=now > loan.due_at,
            assessed_fine=assessed_fine,
        )

    def renew(self, actor_id: int, loan_id: int) -> LoanView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            loan = unit_of_work.loans.get_by_id(loan_id)
            if loan is None:
                raise CirculationNotFoundError(f"Loan {loan_id} was not found.")
            copy = self._get_copy(unit_of_work, loan.book_copy_id)
            unit_of_work.lock_rows(
                users=(actor_id, loan.user_id),
                books=(copy.book_id,),
                book_copies=(copy.id,) if copy.id is not None else (),
                loans=(loan_id,),
            )
            actor = require_active_user(unit_of_work, actor_id)
            loan = unit_of_work.loans.get_by_id(loan_id)
            if loan is None:
                raise CirculationNotFoundError(f"Loan {loan_id} was not found.")
            if loan.returned_at is not None or loan.id is None:
                raise RenewalNotAllowedError("Only an active loan can be renewed.")
            if actor.id != loan.user_id and actor.role not in CIRCULATION_STAFF_ROLES:
                raise AuthorizationError("You may only renew your own loans.")
            if now >= loan.due_at:
                raise RenewalNotAllowedError("An overdue loan cannot be renewed.")
            if loan.renewal_count >= self._policy.maximum_renewals:
                raise RenewalNotAllowedError("This loan has reached its renewal limit.")
            copy = self._get_copy(unit_of_work, loan.book_copy_id)
            book = self._get_book(unit_of_work, copy.book_id)
            if unit_of_work.reservations.list_active_for_book(copy.book_id):
                raise RenewalNotAllowedError(
                    "This loan cannot be renewed while the book has an active reservation."
                )
            borrower = self._get_user(unit_of_work, loan.user_id)
            renewed = replace(
                loan,
                due_at=loan.due_at + self._policy.loan_period,
                renewal_count=loan.renewal_count + 1,
            )
            unit_of_work.loans.renew(loan.id, renewed.due_at, renewed.renewal_count)
            unit_of_work.commit()

        return LoanView(
            loan=renewed,
            book=book,
            copy=copy,
            borrower_username=borrower.username,
            is_overdue=False,
        )

    def list_loans(self, actor_id: int, username: str | None = None) -> list[LoanView]:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_active_user(unit_of_work, actor_id)
            borrower = actor if username is None else unit_of_work.users.get_by_username(username)
            if borrower is None or borrower.id is None:
                raise CirculationNotFoundError("The borrower account was not found.")
            if borrower.id != actor.id and actor.role not in CIRCULATION_STAFF_ROLES:
                raise AuthorizationError("You may only inspect your own loans.")
            loans = unit_of_work.loans.list_for_user(borrower.id)
            return [self._loan_view(unit_of_work, item, borrower, now) for item in loans]

    def _reservation_view(
        self, unit_of_work: UnitOfWork, reservation: Reservation
    ) -> ReservationView:
        book = self._get_book(unit_of_work, reservation.book_id)
        position = None
        if reservation.status is ReservationStatus.ACTIVE:
            queue = unit_of_work.reservations.list_active_for_book(reservation.book_id)
            position = self._queue_position(queue, reservation.id)
        return ReservationView(reservation, book.title, position)

    def _loan_view(
        self,
        unit_of_work: UnitOfWork,
        loan: Loan,
        borrower: User,
        now: datetime,
    ) -> LoanView:
        copy = self._get_copy(unit_of_work, loan.book_copy_id)
        book = self._get_book(unit_of_work, copy.book_id)
        return LoanView(
            loan=loan,
            book=book,
            copy=copy,
            borrower_username=borrower.username,
            is_overdue=loan.returned_at is None and now > loan.due_at,
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Circulation clock must return a timezone-aware timestamp.")
        return value.astimezone(UTC)

    @staticmethod
    def _queue_position(queue: list[Reservation], reservation_id: int | None) -> int:
        for position, reservation in enumerate(queue, start=1):
            if reservation.id == reservation_id:
                return position
        raise RuntimeError("Reservation is missing from its active queue.")

    @staticmethod
    def _get_book(unit_of_work: UnitOfWork, book_id: int) -> Book:
        book = unit_of_work.books.get_by_id(book_id)
        if book is None:
            raise CirculationNotFoundError(f"Book {book_id} was not found.")
        return book

    @staticmethod
    def _get_copy(unit_of_work: UnitOfWork, copy_id: int) -> BookCopy:
        copy = unit_of_work.book_copies.get_by_id(copy_id)
        if copy is None:
            raise CirculationNotFoundError(f"Book copy {copy_id} was not found.")
        return copy

    @staticmethod
    def _get_user(unit_of_work: UnitOfWork, user_id: int) -> User:
        user = unit_of_work.users.get_by_id(user_id)
        if user is None:
            raise CirculationNotFoundError(f"User {user_id} was not found.")
        return user

    @staticmethod
    def _require_circulation_staff(unit_of_work: UnitOfWork, actor_id: int) -> None:
        require_role(
            unit_of_work,
            actor_id,
            CIRCULATION_STAFF_ROLES,
            "Librarian or administrator permission is required.",
        )
