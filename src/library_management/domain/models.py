"""Validated domain entities with no UI or persistence dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from library_management.domain.enums import (
    BookCopyStatus,
    FeedbackStatus,
    FineSettlementKind,
    FineStatus,
    RequestStatus,
    ReservationStatus,
    UserRole,
)
from library_management.domain.exceptions import DomainValidationError

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
BARCODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,63}$")
MONEY_QUANTUM = Decimal("0.01")


def utc_now() -> datetime:
    return datetime.now(UTC)


def _required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise DomainValidationError(f"{field_name} must not be empty.")
    return cleaned


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_isbn(value: str | None) -> str | None:
    """Normalize and checksum-validate an optional ISBN-10 or ISBN-13."""
    cleaned = _optional_text(value)
    if cleaned is None:
        return None
    compact = re.sub(r"[-\s]", "", cleaned).upper()
    if len(compact) == 10 and compact[:9].isdigit() and (compact[9].isdigit() or compact[9] == "X"):
        values = [int(character) for character in compact[:9]]
        values.append(10 if compact[9] == "X" else int(compact[9]))
        checksum = sum(
            weight * digit for weight, digit in zip(range(10, 0, -1), values, strict=True)
        )
        if checksum % 11 == 0:
            return compact
    elif len(compact) == 13 and compact.isdigit():
        checksum = sum(
            int(character) * (1 if index % 2 == 0 else 3) for index, character in enumerate(compact)
        )
        if checksum % 10 == 0:
            return compact
    raise DomainValidationError("ISBN must be a valid ISBN-10 or ISBN-13.")


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError(f"{field_name} must include timezone information.")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class User:
    display_name: str
    username: str
    password_hash: str
    role: UserRole = UserRole.MEMBER
    id: int | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "display_name", _required_text(self.display_name, "Display name"))
        normalized_username = self.username.strip().casefold()
        if not USERNAME_PATTERN.fullmatch(normalized_username):
            raise DomainValidationError(
                "Username must contain 3-32 lowercase letters, numbers, dots, "
                "hyphens, or underscores."
            )
        object.__setattr__(self, "username", normalized_username)
        object.__setattr__(
            self, "password_hash", _required_text(self.password_hash, "Password hash")
        )
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "Created timestamp"))


@dataclass(frozen=True, slots=True)
class Book:
    title: str
    author: str
    publication_year: int
    id: int | None = None
    isbn: str | None = None
    category: str | None = None
    description: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _required_text(self.title, "Title"))
        object.__setattr__(self, "author", _required_text(self.author, "Author"))
        if not 0 < self.publication_year <= date.today().year + 1:
            raise DomainValidationError("Publication year is outside the supported range.")
        object.__setattr__(self, "isbn", normalize_isbn(self.isbn))
        object.__setattr__(self, "category", _optional_text(self.category))
        object.__setattr__(self, "description", _optional_text(self.description))
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "Created timestamp"))


@dataclass(frozen=True, slots=True)
class BookCopy:
    book_id: int
    barcode: str
    status: BookCopyStatus = BookCopyStatus.AVAILABLE
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.book_id <= 0:
            raise DomainValidationError("Book identifier must be positive.")
        normalized_barcode = _required_text(self.barcode, "Barcode").upper()
        if not BARCODE_PATTERN.fullmatch(normalized_barcode):
            raise DomainValidationError(
                "Barcode must contain 3-64 letters, numbers, dots, hyphens, or underscores."
            )
        object.__setattr__(self, "barcode", normalized_barcode)
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "Created timestamp"))


@dataclass(frozen=True, slots=True)
class Reservation:
    user_id: int
    book_id: int
    status: ReservationStatus = ReservationStatus.ACTIVE
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.user_id <= 0 or self.book_id <= 0:
            raise DomainValidationError("Reservation identifiers must be positive.")
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "Created timestamp"))
        if self.resolved_at is not None:
            object.__setattr__(
                self, "resolved_at", _utc_datetime(self.resolved_at, "Resolved timestamp")
            )
        if self.status is ReservationStatus.ACTIVE and self.resolved_at is not None:
            raise DomainValidationError("An active reservation cannot have a resolution timestamp.")
        if self.status is not ReservationStatus.ACTIVE and self.resolved_at is None:
            raise DomainValidationError("A resolved reservation requires a resolution timestamp.")


@dataclass(frozen=True, slots=True)
class Loan:
    user_id: int
    book_copy_id: int
    checked_out_at: datetime
    due_at: datetime
    id: int | None = None
    returned_at: datetime | None = None
    renewal_count: int = 0

    def __post_init__(self) -> None:
        if self.user_id <= 0 or self.book_copy_id <= 0:
            raise DomainValidationError("Loan identifiers must be positive.")
        if self.renewal_count < 0:
            raise DomainValidationError("Renewal count cannot be negative.")
        checked_out_at = _utc_datetime(self.checked_out_at, "Checkout timestamp")
        due_at = _utc_datetime(self.due_at, "Due timestamp")
        if due_at <= checked_out_at:
            raise DomainValidationError("Due timestamp must be after checkout.")
        object.__setattr__(self, "checked_out_at", checked_out_at)
        object.__setattr__(self, "due_at", due_at)
        if self.returned_at is not None:
            returned_at = _utc_datetime(self.returned_at, "Return timestamp")
            if returned_at < checked_out_at:
                raise DomainValidationError("Return timestamp cannot precede checkout.")
            object.__setattr__(self, "returned_at", returned_at)


@dataclass(frozen=True, slots=True)
class Fine:
    user_id: int
    reason: str
    amount: Decimal
    status: FineStatus = FineStatus.OUTSTANDING
    id: int | None = None
    loan_id: int | None = None
    assessed_at: datetime = field(default_factory=utc_now)
    settled_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.user_id <= 0 or (self.loan_id is not None and self.loan_id <= 0):
            raise DomainValidationError("Fine identifiers must be positive.")
        object.__setattr__(self, "reason", _required_text(self.reason, "Fine reason"))
        if (
            not self.amount.is_finite()
            or self.amount <= 0
            or self.amount.quantize(MONEY_QUANTUM) != self.amount
        ):
            raise DomainValidationError(
                "Fine amount must be positive with at most two decimal places."
            )
        object.__setattr__(self, "amount", self.amount.quantize(MONEY_QUANTUM))
        object.__setattr__(
            self, "assessed_at", _utc_datetime(self.assessed_at, "Assessment timestamp")
        )
        if self.settled_at is not None:
            object.__setattr__(
                self, "settled_at", _utc_datetime(self.settled_at, "Settlement timestamp")
            )
        if self.status is FineStatus.OUTSTANDING and self.settled_at is not None:
            raise DomainValidationError("An outstanding fine cannot have a settlement timestamp.")
        if self.status is not FineStatus.OUTSTANDING and self.settled_at is None:
            raise DomainValidationError("A settled fine requires a settlement timestamp.")


@dataclass(frozen=True, slots=True)
class FineSettlement:
    fine_id: int
    recorded_by_user_id: int
    kind: FineSettlementKind
    amount: Decimal
    id: int | None = None
    note: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.fine_id <= 0 or self.recorded_by_user_id <= 0:
            raise DomainValidationError("Fine settlement identifiers must be positive.")
        if (
            not self.amount.is_finite()
            or self.amount <= 0
            or self.amount.quantize(MONEY_QUANTUM) != self.amount
        ):
            raise DomainValidationError(
                "Settlement amount must be positive with at most two decimal places."
            )
        object.__setattr__(self, "amount", self.amount.quantize(MONEY_QUANTUM))
        object.__setattr__(self, "note", _optional_text(self.note))
        object.__setattr__(
            self, "created_at", _utc_datetime(self.created_at, "Settlement timestamp")
        )


@dataclass(frozen=True, slots=True)
class BookRequest:
    user_id: int
    title: str
    author: str
    publication_year: int | None = None
    status: RequestStatus = RequestStatus.PENDING
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    reviewed_by_user_id: int | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    acquired_book_id: int | None = None
    acquired_by_user_id: int | None = None
    acquired_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise DomainValidationError("User identifier must be positive.")
        object.__setattr__(self, "title", _required_text(self.title, "Title"))
        object.__setattr__(self, "author", _required_text(self.author, "Author"))
        if (
            self.publication_year is not None
            and not 0 < self.publication_year <= date.today().year + 1
        ):
            raise DomainValidationError("Publication year is outside the supported range.")
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "Created timestamp"))
        for identifier in (
            self.reviewed_by_user_id,
            self.acquired_book_id,
            self.acquired_by_user_id,
        ):
            if identifier is not None and identifier <= 0:
                raise DomainValidationError("Request identifiers must be positive.")
        if self.reviewed_at is not None:
            object.__setattr__(
                self, "reviewed_at", _utc_datetime(self.reviewed_at, "Review timestamp")
            )
        if self.acquired_at is not None:
            object.__setattr__(
                self, "acquired_at", _utc_datetime(self.acquired_at, "Acquisition timestamp")
            )
        object.__setattr__(self, "review_note", _optional_text(self.review_note))
        review_fields = (self.reviewed_by_user_id, self.reviewed_at)
        acquisition_fields = (self.acquired_book_id, self.acquired_by_user_id, self.acquired_at)
        if self.status is RequestStatus.PENDING:
            if any(
                value is not None
                for value in (*review_fields, self.review_note, *acquisition_fields)
            ):
                raise DomainValidationError("A pending request cannot contain review metadata.")
            return
        if any(value is None for value in review_fields):
            raise DomainValidationError("A reviewed request requires reviewer and timestamp.")
        if self.status is RequestStatus.REJECTED and self.review_note is None:
            raise DomainValidationError("A rejected request requires a review note.")
        if self.status is RequestStatus.ACQUIRED:
            if any(value is None for value in acquisition_fields):
                raise DomainValidationError(
                    "An acquired request requires book, staff, and timestamp metadata."
                )
        elif any(value is not None for value in acquisition_fields):
            raise DomainValidationError(
                "Only an acquired request can contain acquisition metadata."
            )


@dataclass(frozen=True, slots=True)
class Feedback:
    content: str
    user_id: int | None = None
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    status: FeedbackStatus = FeedbackStatus.NEW
    reviewed_by_user_id: int | None = None
    reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.user_id is not None and self.user_id <= 0:
            raise DomainValidationError("User identifier must be positive.")
        object.__setattr__(self, "content", _required_text(self.content, "Feedback"))
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "Created timestamp"))
        if self.reviewed_by_user_id is not None and self.reviewed_by_user_id <= 0:
            raise DomainValidationError("Feedback reviewer identifier must be positive.")
        if self.reviewed_at is not None:
            object.__setattr__(
                self, "reviewed_at", _utc_datetime(self.reviewed_at, "Review timestamp")
            )
        if self.status is FeedbackStatus.NEW:
            if self.reviewed_by_user_id is not None or self.reviewed_at is not None:
                raise DomainValidationError("New feedback cannot contain review metadata.")
        elif self.reviewed_by_user_id is None or self.reviewed_at is None:
            raise DomainValidationError("Reviewed feedback requires reviewer and timestamp.")
