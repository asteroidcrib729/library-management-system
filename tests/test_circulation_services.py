from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial

import pytest

from library_management.database import Database
from library_management.domain import (
    Book,
    BookCopy,
    BookCopyStatus,
    ReservationStatus,
    User,
    UserRole,
)
from library_management.repositories import UnitOfWork
from library_management.repositories.sqlite import SqliteUnitOfWork
from library_management.services import (
    AuthorizationError,
    CirculationPolicy,
    CirculationService,
    FinePolicy,
    LoanLimitError,
    RenewalNotAllowedError,
    ReservationConflictError,
    ReservationQueueError,
)

NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


class AdjustableClock:
    def __init__(self, current: datetime = NOW) -> None:
        self.current = current

    def __call__(self) -> datetime:
        return self.current


def build_factory(database: Database) -> Callable[[], UnitOfWork]:
    return partial(SqliteUnitOfWork, database)


def add_user(database: Database, username: str, role: UserRole = UserRole.MEMBER) -> User:
    with SqliteUnitOfWork(database) as unit_of_work:
        user = unit_of_work.users.add(
            User(
                display_name=username,
                username=username,
                password_hash="$argon2id$test-hash",
                role=role,
            )
        )
        unit_of_work.commit()
    return user


def add_book_and_copy(
    database: Database, title: str = "Dune", barcode: str = "COPY-001"
) -> tuple[Book, BookCopy]:
    with SqliteUnitOfWork(database) as unit_of_work:
        book = unit_of_work.books.add(
            Book(title=title, author="Frank Herbert", publication_year=1965)
        )
        copy = unit_of_work.book_copies.add(BookCopy(book_id=book.id or 0, barcode=barcode))
        unit_of_work.commit()
    return book, copy


def build_service(
    database: Database,
    *,
    policy: CirculationPolicy | None = None,
    clock: AdjustableClock | None = None,
    fine_policy: FinePolicy | None = None,
) -> CirculationService:
    return CirculationService(
        build_factory(database),
        policy=policy,
        fine_policy=fine_policy,
        clock=clock or AdjustableClock(),
    )


def test_reservation_queue_positions_close_after_cancellation(database: Database) -> None:
    service = build_service(database)
    first = add_user(database, "reader.one")
    second = add_user(database, "reader.two")
    book, _ = add_book_and_copy(database)

    first_view = service.reserve(first.id or 0, book.id or 0)
    second_view = service.reserve(second.id or 0, book.id or 0)
    service.cancel_reservation(first.id or 0, first_view.reservation.id or 0)
    second_history = service.list_reservations(second.id or 0)

    assert first_view.queue_position == 1
    assert second_view.queue_position == 2
    assert second_history[0].queue_position == 1


def test_duplicate_reservation_is_rejected(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    book, _ = add_book_and_copy(database)
    service.reserve(member.id or 0, book.id or 0)

    with pytest.raises(ReservationConflictError, match="already have"):
        service.reserve(member.id or 0, book.id or 0)


def test_checkout_requires_staff_and_honors_reservation_queue(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    first = add_user(database, "reader.one")
    second = add_user(database, "reader.two")
    book, copy = add_book_and_copy(database)
    service.reserve(first.id or 0, book.id or 0)

    with pytest.raises(AuthorizationError, match="Librarian or administrator"):
        service.checkout(second.id or 0, first.username, copy.barcode)
    with pytest.raises(ReservationQueueError):
        service.checkout(librarian.id or 0, second.username, copy.barcode)

    view = service.checkout(librarian.id or 0, first.username, copy.barcode)

    assert view.loan.due_at == NOW + timedelta(days=14)
    assert view.copy.status is BookCopyStatus.ON_LOAN
    history = service.list_reservations(first.id or 0)
    assert history[0].reservation.status is ReservationStatus.FULFILLED
    assert history[0].queue_position is None


def test_checkout_failure_does_not_change_copy_or_create_loan(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    first = add_user(database, "reader.one")
    second = add_user(database, "reader.two")
    book, copy = add_book_and_copy(database)
    service.reserve(first.id or 0, book.id or 0)

    with pytest.raises(ReservationQueueError):
        service.checkout(librarian.id or 0, second.username, copy.barcode)

    with SqliteUnitOfWork(database) as unit_of_work:
        stored_copy = unit_of_work.book_copies.get_by_id(copy.id or 0)
        active_loan = unit_of_work.loans.get_active_by_copy(copy.id or 0)

    assert stored_copy is not None
    assert stored_copy.status is BookCopyStatus.AVAILABLE
    assert active_loan is None


def test_return_closes_loan_and_makes_copy_available(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    member = add_user(database, "reader.one")
    _, copy = add_book_and_copy(database)
    checked_out = service.checkout(librarian.id or 0, member.username, copy.barcode)

    returned = service.return_copy(librarian.id or 0, copy.barcode)

    assert returned.loan.id == checked_out.loan.id
    assert returned.loan.returned_at == NOW
    assert returned.copy.status is BookCopyStatus.AVAILABLE
    assert returned.assessed_fine is None


def test_overdue_return_assesses_started_days_atomically(database: Database) -> None:
    clock = AdjustableClock()
    service = build_service(
        database,
        clock=clock,
        fine_policy=FinePolicy(daily_overdue_rate=Decimal("10.00")),
    )
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    member = add_user(database, "reader.one")
    _, copy = add_book_and_copy(database)
    checked_out = service.checkout(librarian.id or 0, member.username, copy.barcode)
    clock.current = checked_out.loan.due_at + timedelta(days=1, microseconds=1)

    returned = service.return_copy(librarian.id or 0, copy.barcode)

    assert returned.assessed_fine is not None
    assert returned.assessed_fine.loan_id == checked_out.loan.id
    assert returned.assessed_fine.amount == Decimal("20.00")
    with SqliteUnitOfWork(database) as unit_of_work:
        stored_fine = unit_of_work.fines.get_by_loan_id(checked_out.loan.id or 0)
        stored_copy = unit_of_work.book_copies.get_by_id(copy.id or 0)
    assert stored_fine == returned.assessed_fine
    assert stored_copy is not None
    assert stored_copy.status is BookCopyStatus.AVAILABLE


def test_active_loan_limit_is_enforced(database: Database) -> None:
    policy = CirculationPolicy(maximum_active_loans=1)
    service = build_service(database, policy=policy)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    member = add_user(database, "reader.one")
    _, first_copy = add_book_and_copy(database)
    _, second_copy = add_book_and_copy(database, title="Dune Messiah", barcode="COPY-002")
    service.checkout(librarian.id or 0, member.username, first_copy.barcode)

    with pytest.raises(LoanLimitError):
        service.checkout(librarian.id or 0, member.username, second_copy.barcode)


def test_renewal_extends_due_date_and_enforces_limit(database: Database) -> None:
    policy = CirculationPolicy(maximum_renewals=2)
    service = build_service(database, policy=policy)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    member = add_user(database, "reader.one")
    _, copy = add_book_and_copy(database)
    checkout = service.checkout(librarian.id or 0, member.username, copy.barcode)

    first = service.renew(member.id or 0, checkout.loan.id or 0)
    second = service.renew(member.id or 0, checkout.loan.id or 0)

    assert first.loan.due_at == checkout.loan.due_at + timedelta(days=14)
    assert second.loan.due_at == checkout.loan.due_at + timedelta(days=28)
    assert second.loan.renewal_count == 2
    with pytest.raises(RenewalNotAllowedError, match="renewal limit"):
        service.renew(member.id or 0, checkout.loan.id or 0)


def test_active_reservation_blocks_renewal(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    borrower = add_user(database, "reader.one")
    waiting = add_user(database, "reader.two")
    book, copy = add_book_and_copy(database)
    checkout = service.checkout(librarian.id or 0, borrower.username, copy.barcode)
    service.reserve(waiting.id or 0, book.id or 0)

    with pytest.raises(RenewalNotAllowedError, match="active reservation"):
        service.renew(borrower.id or 0, checkout.loan.id or 0)


def test_overdue_loan_cannot_be_renewed(database: Database) -> None:
    clock = AdjustableClock()
    service = build_service(database, clock=clock)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    member = add_user(database, "reader.one")
    _, copy = add_book_and_copy(database)
    checkout = service.checkout(librarian.id or 0, member.username, copy.barcode)
    clock.current = checkout.loan.due_at

    with pytest.raises(RenewalNotAllowedError, match="overdue"):
        service.renew(member.id or 0, checkout.loan.id or 0)


def test_member_cannot_view_or_renew_another_users_loan(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    borrower = add_user(database, "reader.one")
    other = add_user(database, "reader.two")
    _, copy = add_book_and_copy(database)
    checkout = service.checkout(librarian.id or 0, borrower.username, copy.barcode)

    with pytest.raises(AuthorizationError, match="inspect your own"):
        service.list_loans(other.id or 0, borrower.username)
    with pytest.raises(AuthorizationError, match="renew your own"):
        service.renew(other.id or 0, checkout.loan.id or 0)

    staff_view = service.list_loans(librarian.id or 0, borrower.username)
    assert staff_view[0].loan.id == checkout.loan.id


def test_user_cannot_reserve_book_already_on_loan_to_them(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    borrower = add_user(database, "reader.one")
    book, copy = add_book_and_copy(database)
    service.checkout(librarian.id or 0, borrower.username, copy.barcode)

    with pytest.raises(ReservationConflictError, match="already on loan"):
        service.reserve(borrower.id or 0, book.id or 0)
