"""Typed public HTTP contract; password and persistence details stay private."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from library_management.domain import (
    BookCopyStatus,
    FeedbackStatus,
    FineSettlementKind,
    FineStatus,
    RequestStatus,
    ReservationStatus,
    UserRole,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)


class ErrorResponse(ApiModel):
    code: str
    message: str
    request_id: str


class PrincipalResponse(ApiModel):
    user_id: int
    display_name: str
    username: str
    role: UserRole


class SessionResponse(ApiModel):
    principal: PrincipalResponse
    csrf_token: str
    expires_at: datetime


class LoginRequest(ApiModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class AccountRequest(ApiModel):
    display_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=12, max_length=128)


class DeactivateAccountRequest(ApiModel):
    username: str = Field(min_length=3, max_length=32)


class BookResponse(ApiModel):
    id: int
    title: str
    author: str
    publication_year: int
    isbn: str | None
    category: str | None
    description: str | None
    created_at: datetime


class BookCopyResponse(ApiModel):
    id: int
    book_id: int
    barcode: str
    status: BookCopyStatus
    created_at: datetime


class CatalogEntryResponse(ApiModel):
    book: BookResponse
    total_copies: int
    available_copies: int


class BookRequestBody(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    author: str = Field(min_length=1, max_length=200)
    publication_year: int = Field(ge=1, le=9999)
    isbn: str | None = Field(default=None, max_length=32)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=4000)


class CopyRequest(ApiModel):
    barcode: str = Field(min_length=3, max_length=64)


class CopyStatusRequest(ApiModel):
    status: BookCopyStatus


class ReservationResponse(ApiModel):
    id: int
    user_id: int
    book_id: int
    status: ReservationStatus
    created_at: datetime
    resolved_at: datetime | None


class ReservationViewResponse(ApiModel):
    reservation: ReservationResponse
    book_title: str
    queue_position: int | None


class CheckoutRequest(ApiModel):
    borrower_username: str = Field(min_length=3, max_length=32)
    barcode: str = Field(min_length=3, max_length=64)


class ReturnRequest(ApiModel):
    barcode: str = Field(min_length=3, max_length=64)


class LoanResponse(ApiModel):
    id: int
    user_id: int
    book_copy_id: int
    checked_out_at: datetime
    due_at: datetime
    returned_at: datetime | None
    renewal_count: int


class FineResponse(ApiModel):
    id: int
    user_id: int
    reason: str
    amount: Decimal
    status: FineStatus
    loan_id: int | None
    assessed_at: datetime
    settled_at: datetime | None


class LoanViewResponse(ApiModel):
    loan: LoanResponse
    book: BookResponse
    book_copy: BookCopyResponse = Field(validation_alias="copy", serialization_alias="copy")
    borrower_username: str
    is_overdue: bool
    assessed_fine: FineResponse | None


class SettlementResponse(ApiModel):
    id: int
    fine_id: int
    recorded_by_user_id: int
    kind: FineSettlementKind
    amount: Decimal
    note: str | None
    created_at: datetime


class FineViewResponse(ApiModel):
    fine: FineResponse
    username: str
    settlement: SettlementResponse | None
    settlement_actor_username: str | None


class ManualFineRequest(ApiModel):
    username: str = Field(min_length=3, max_length=32)
    amount: Decimal = Field(gt=Decimal("0"), decimal_places=2, max_digits=12)
    reason: str = Field(min_length=1, max_length=500)


class NoteRequest(ApiModel):
    note: str | None = Field(default=None, max_length=500)


class WaiverRequest(ApiModel):
    reason: str = Field(min_length=1, max_length=500)


class AcquisitionRequestBody(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    author: str = Field(min_length=1, max_length=200)
    publication_year: int | None = Field(default=None, ge=1, le=9999)


class ReviewRequest(ApiModel):
    status: RequestStatus
    note: str | None = Field(default=None, max_length=1000)


class AcquiredRequest(ApiModel):
    book_id: int = Field(gt=0)


class BookRequestResponse(ApiModel):
    id: int
    user_id: int
    title: str
    author: str
    publication_year: int | None
    status: RequestStatus
    created_at: datetime
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    review_note: str | None
    acquired_book_id: int | None
    acquired_by_user_id: int | None
    acquired_at: datetime | None


class BookRequestViewResponse(ApiModel):
    request: BookRequestResponse
    username: str
    reviewer_username: str | None
    acquired_book_title: str | None
    acquisition_actor_username: str | None


class FeedbackRequest(ApiModel):
    content: str = Field(min_length=1, max_length=4000)


class FeedbackResponse(ApiModel):
    id: int
    content: str
    user_id: int | None
    created_at: datetime
    status: FeedbackStatus
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None


class FeedbackViewResponse(ApiModel):
    feedback: FeedbackResponse
    username: str
    reviewer_username: str | None


class RecommendationResponse(ApiModel):
    book: BookResponse
    score: int
    reason: str
    available_copies: int
    historical_checkouts: int


class PopularBookResponse(ApiModel):
    book: BookResponse
    historical_checkouts: int
    available_copies: int


class OperationalReportResponse(ApiModel):
    generated_at: datetime
    active_users: int
    catalog_titles: int
    total_copies: int
    available_copies: int
    active_loans: int
    overdue_loans: int
    active_reservations: int
    outstanding_fines: int
    outstanding_fine_amount: Decimal
    pending_requests: int
    new_feedback: int
    popular_books: tuple[PopularBookResponse, ...]
