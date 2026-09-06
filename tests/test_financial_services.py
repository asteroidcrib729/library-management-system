from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial

import pytest

from library_management.database import Database
from library_management.domain import FineSettlementKind, FineStatus, User, UserRole
from library_management.repositories import UnitOfWork
from library_management.repositories.sqlite import SqliteUnitOfWork
from library_management.services import (
    AuthorizationError,
    FinancialNotFoundError,
    FinancialService,
    FinePolicy,
    FineSettlementError,
)

NOW = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


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


def build_service(database: Database) -> FinancialService:
    return FinancialService(build_factory(database), clock=lambda: NOW)


def assess_fine(
    service: FinancialService,
    staff: User,
    member: User,
    amount: Decimal = Decimal("25.50"),
) -> int:
    view = service.assess_manual(staff.id or 0, member.username, amount, "Damaged cover")
    return view.fine.id or 0


def test_fine_policy_charges_each_started_overdue_day() -> None:
    policy = FinePolicy(daily_overdue_rate=Decimal("10"), currency_code="pkr")
    due_at = NOW

    assert policy.currency_code == "PKR"
    assert policy.overdue_amount(due_at, due_at) == Decimal("0.00")
    assert policy.overdue_amount(due_at, due_at + timedelta(microseconds=1)) == Decimal("10.00")
    assert policy.overdue_amount(due_at, due_at + timedelta(days=2)) == Decimal("20.00")


def test_staff_can_assess_manual_fine_with_minor_unit_persistence(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    member = add_user(database, "reader.one")

    fine_id = assess_fine(service, librarian, member)
    views = service.list_fines(member.id or 0)

    assert views[0].fine.id == fine_id
    assert views[0].fine.amount == Decimal("25.50")
    assert views[0].fine.status is FineStatus.OUTSTANDING
    with database.connect() as connection:
        amount_minor = connection.execute(
            "SELECT amount_minor FROM fines WHERE id = ?", (fine_id,)
        ).fetchone()[0]
    assert amount_minor == 2550


def test_member_cannot_assess_or_inspect_another_users_fines(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    owner = add_user(database, "reader.one")
    other = add_user(database, "reader.two")
    assess_fine(service, librarian, owner)

    with pytest.raises(AuthorizationError):
        service.assess_manual(other.id or 0, owner.username, Decimal("10.00"), "Charge")
    with pytest.raises(AuthorizationError, match="own fines"):
        service.list_fines(other.id or 0, owner.username)


def test_staff_can_record_full_payment_with_immutable_history(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    member = add_user(database, "reader.one")
    fine_id = assess_fine(service, librarian, member)

    paid = service.record_payment(librarian.id or 0, fine_id, "Receipt 42")

    assert paid.fine.status is FineStatus.PAID
    assert paid.fine.settled_at == NOW
    assert paid.settlement is not None
    assert paid.settlement.kind is FineSettlementKind.PAYMENT
    assert paid.settlement.amount == paid.fine.amount
    assert paid.settlement.note == "Receipt 42"
    assert paid.settlement_actor_username == librarian.username
    detail = service.get_fine(member.id or 0, fine_id)
    assert detail.settlement == paid.settlement
    with pytest.raises(FineSettlementError, match="outstanding"):
        service.record_payment(librarian.id or 0, fine_id)


def test_only_administrator_can_waive_with_reason(database: Database) -> None:
    service = build_service(database)
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    administrator = add_user(database, "admin.one", UserRole.ADMINISTRATOR)
    member = add_user(database, "reader.one")
    fine_id = assess_fine(service, librarian, member)

    with pytest.raises(AuthorizationError, match="Administrator"):
        service.waive(librarian.id or 0, fine_id, "Courtesy")
    with pytest.raises(FineSettlementError, match="reason"):
        service.waive(administrator.id or 0, fine_id, "  ")

    waived = service.waive(administrator.id or 0, fine_id, "Staff correction")

    assert waived.fine.status is FineStatus.WAIVED
    assert waived.settlement is not None
    assert waived.settlement.kind is FineSettlementKind.WAIVER
    assert waived.settlement.note == "Staff correction"


def test_payment_requires_staff_and_existing_fine(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)

    with pytest.raises(AuthorizationError):
        service.record_payment(member.id or 0, 999)
    with pytest.raises(FinancialNotFoundError, match="Fine 999"):
        service.record_payment(librarian.id or 0, 999)
