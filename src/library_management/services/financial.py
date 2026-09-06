"""Fine assessment, settlement, and financial-history use cases."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from library_management.domain import (
    Fine,
    FineSettlement,
    FineSettlementKind,
    FineStatus,
    User,
    UserRole,
)
from library_management.repositories import DuplicateRecordError, UnitOfWork
from library_management.services.accounts import UnitOfWorkFactory
from library_management.services.authorization import require_active_user, require_role
from library_management.services.errors import (
    AuthorizationError,
    FinancialNotFoundError,
    FineSettlementError,
)

Clock = Callable[[], datetime]
FINANCIAL_STAFF_ROLES = frozenset({UserRole.LIBRARIAN, UserRole.ADMINISTRATOR})


def system_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class FinePolicy:
    daily_overdue_rate: Decimal = Decimal("10.00")
    currency_code: str = "PKR"

    def __post_init__(self) -> None:
        if (
            not self.daily_overdue_rate.is_finite()
            or self.daily_overdue_rate <= 0
            or self.daily_overdue_rate.quantize(Decimal("0.01")) != self.daily_overdue_rate
        ):
            raise ValueError("Daily overdue rate must be positive with at most two decimals.")
        currency = self.currency_code.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("Currency code must contain three letters.")
        object.__setattr__(
            self, "daily_overdue_rate", self.daily_overdue_rate.quantize(Decimal("0.01"))
        )
        object.__setattr__(self, "currency_code", currency)

    def overdue_days(self, due_at: datetime, returned_at: datetime) -> int:
        if returned_at <= due_at:
            return 0
        elapsed = returned_at - due_at
        complete_days, remainder = divmod(elapsed, timedelta(days=1))
        return complete_days + (1 if remainder else 0)

    def overdue_amount(self, due_at: datetime, returned_at: datetime) -> Decimal:
        return self.daily_overdue_rate * self.overdue_days(due_at, returned_at)


@dataclass(frozen=True, slots=True)
class FineView:
    fine: Fine
    username: str
    settlement: FineSettlement | None
    settlement_actor_username: str | None = None


class FinancialService:
    """Manage auditable charges and full settlements."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        policy: FinePolicy | None = None,
        clock: Clock = system_clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._policy = policy or FinePolicy()
        self._clock = clock

    @property
    def currency_code(self) -> str:
        return self._policy.currency_code

    def list_fines(self, actor_id: int, username: str | None = None) -> list[FineView]:
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_active_user(unit_of_work, actor_id)
            owner = actor if username is None else unit_of_work.users.get_by_username(username)
            if owner is None or owner.id is None:
                raise FinancialNotFoundError("The account was not found.")
            if owner.id != actor.id and actor.role not in FINANCIAL_STAFF_ROLES:
                raise AuthorizationError("You may only inspect your own fines.")
            return [
                self._view(unit_of_work, fine, owner)
                for fine in unit_of_work.fines.list_for_user(owner.id)
            ]

    def get_fine(self, actor_id: int, fine_id: int) -> FineView:
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_active_user(unit_of_work, actor_id)
            fine = self._get_fine(unit_of_work, fine_id)
            if actor.id != fine.user_id and actor.role not in FINANCIAL_STAFF_ROLES:
                raise AuthorizationError("You may only inspect your own fines.")
            owner = self._get_user(unit_of_work, fine.user_id)
            return self._view(unit_of_work, fine, owner)

    def assess_manual(
        self,
        actor_id: int,
        username: str,
        amount: Decimal,
        reason: str,
    ) -> FineView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            require_role(
                unit_of_work,
                actor_id,
                FINANCIAL_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            owner = unit_of_work.users.get_by_username(username)
            if owner is None or owner.id is None or not owner.is_active:
                raise FinancialNotFoundError("An active account was not found.")
            unit_of_work.lock_rows(users=(actor_id, owner.id))
            require_role(
                unit_of_work,
                actor_id,
                FINANCIAL_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            owner = unit_of_work.users.get_by_id(owner.id)
            if owner is None or owner.id is None or not owner.is_active:
                raise FinancialNotFoundError("An active account was not found.")
            saved = unit_of_work.fines.add(
                Fine(user_id=owner.id, amount=amount, reason=reason, assessed_at=now)
            )
            unit_of_work.commit()
        return FineView(saved, owner.username, None)

    def record_payment(self, actor_id: int, fine_id: int, note: str | None = None) -> FineView:
        return self._settle(actor_id, fine_id, FineSettlementKind.PAYMENT, note)

    def waive(self, actor_id: int, fine_id: int, reason: str) -> FineView:
        if not reason.strip():
            raise FineSettlementError("A waiver reason is required.")
        return self._settle(actor_id, fine_id, FineSettlementKind.WAIVER, reason)

    def _settle(
        self,
        actor_id: int,
        fine_id: int,
        kind: FineSettlementKind,
        note: str | None,
    ) -> FineView:
        now = self._now()
        allowed_roles = (
            frozenset({UserRole.ADMINISTRATOR})
            if kind is FineSettlementKind.WAIVER
            else FINANCIAL_STAFF_ROLES
        )
        message = (
            "Administrator permission is required to waive a fine."
            if kind is FineSettlementKind.WAIVER
            else "Librarian or administrator permission is required."
        )
        with self._unit_of_work_factory() as unit_of_work:
            require_role(unit_of_work, actor_id, allowed_roles, message)
            fine = self._get_fine(unit_of_work, fine_id)
            unit_of_work.lock_rows(users=(actor_id, fine.user_id), fines=(fine_id,))
            require_role(unit_of_work, actor_id, allowed_roles, message)
            fine = self._get_fine(unit_of_work, fine_id)
            if fine.status is not FineStatus.OUTSTANDING:
                raise FineSettlementError("Only an outstanding fine can be settled.")
            settlement = FineSettlement(
                fine_id=fine_id,
                recorded_by_user_id=actor_id,
                kind=kind,
                amount=fine.amount,
                note=note,
                created_at=now,
            )
            try:
                saved_settlement = unit_of_work.fine_settlements.add(settlement)
            except DuplicateRecordError as error:
                raise FineSettlementError("This fine has already been settled.") from error
            status = FineStatus.PAID if kind is FineSettlementKind.PAYMENT else FineStatus.WAIVED
            unit_of_work.fines.settle(fine_id, status, now)
            owner = self._get_user(unit_of_work, fine.user_id)
            actor = self._get_user(unit_of_work, actor_id)
            unit_of_work.commit()
        return FineView(
            replace(fine, status=status, settled_at=now),
            owner.username,
            saved_settlement,
            actor.username,
        )

    def _view(self, unit_of_work: UnitOfWork, fine: Fine, owner: User) -> FineView:
        if fine.id is None:
            raise RuntimeError("A stored fine is missing its identifier.")
        settlement = unit_of_work.fine_settlements.get_for_fine(fine.id)
        actor_username = None
        if settlement is not None:
            actor_username = self._get_user(unit_of_work, settlement.recorded_by_user_id).username
        return FineView(fine, owner.username, settlement, actor_username)

    @staticmethod
    def _get_fine(unit_of_work: UnitOfWork, fine_id: int) -> Fine:
        fine = unit_of_work.fines.get_by_id(fine_id)
        if fine is None:
            raise FinancialNotFoundError(f"Fine {fine_id} was not found.")
        return fine

    @staticmethod
    def _get_user(unit_of_work: UnitOfWork, user_id: int) -> User:
        user = unit_of_work.users.get_by_id(user_id)
        if user is None:
            raise FinancialNotFoundError(f"User {user_id} was not found.")
        return user

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Financial clock must return a timezone-aware timestamp.")
        return value.astimezone(UTC)
