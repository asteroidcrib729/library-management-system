"""Enumerated domain states persisted as stable string values."""

from enum import StrEnum


class UserRole(StrEnum):
    MEMBER = "member"
    LIBRARIAN = "librarian"
    ADMINISTRATOR = "administrator"


class BookCopyStatus(StrEnum):
    AVAILABLE = "available"
    ON_LOAN = "on_loan"
    LOST = "lost"
    DAMAGED = "damaged"
    WITHDRAWN = "withdrawn"


class ReservationStatus(StrEnum):
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class FineStatus(StrEnum):
    OUTSTANDING = "outstanding"
    PAID = "paid"
    WAIVED = "waived"


class FineSettlementKind(StrEnum):
    PAYMENT = "payment"
    WAIVER = "waiver"


class RequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACQUIRED = "acquired"


class FeedbackStatus(StrEnum):
    NEW = "new"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"
