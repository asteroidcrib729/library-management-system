from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from library_management.domain import (
    Book,
    BookCopy,
    BookRequest,
    DomainValidationError,
    Feedback,
    FeedbackStatus,
    Fine,
    FineSettlement,
    FineSettlementKind,
    FineStatus,
    Loan,
    RequestStatus,
    Reservation,
    ReservationStatus,
    User,
    normalize_isbn,
)


def test_user_normalizes_username_and_display_name() -> None:
    user = User(
        display_name="  Ada Lovelace  ",
        username="  ADA.Library  ",
        password_hash="$argon2id$example",
    )

    assert user.display_name == "Ada Lovelace"
    assert user.username == "ada.library"


@pytest.mark.parametrize("username", ["ab", "has spaces", "naïve", "-starts-wrong"])
def test_user_rejects_unsupported_usernames(username: str) -> None:
    with pytest.raises(DomainValidationError):
        User(display_name="Reader", username=username, password_hash="hash")


def test_book_requires_a_plausible_publication_year() -> None:
    with pytest.raises(DomainValidationError, match="Publication year"):
        Book(title="A Book", author="An Author", publication_year=0)


def test_book_copy_normalizes_barcode() -> None:
    copy = BookCopy(book_id=1, barcode=" lib-0001 ")

    assert copy.barcode == "LIB-0001"


@pytest.mark.parametrize("barcode", ["x", "contains spaces", "bad/barcode"])
def test_book_copy_rejects_unsupported_barcodes(barcode: str) -> None:
    with pytest.raises(DomainValidationError, match="Barcode"):
        BookCopy(book_id=1, barcode=barcode)


@pytest.mark.parametrize(
    ("supplied", "normalized"),
    [
        ("978-0-441-47812-5", "9780441478125"),
        ("0-306-40615-2", "0306406152"),
    ],
)
def test_isbn_is_normalized_and_checksum_validated(supplied: str, normalized: str) -> None:
    assert normalize_isbn(supplied) == normalized


def test_invalid_isbn_is_rejected() -> None:
    with pytest.raises(DomainValidationError, match="ISBN"):
        normalize_isbn("978-0-441-47812-6")


def test_loan_requires_timezone_aware_ordered_dates() -> None:
    checkout = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(DomainValidationError, match="after checkout"):
        Loan(user_id=1, book_copy_id=1, checked_out_at=checkout, due_at=checkout)

    with pytest.raises(DomainValidationError, match="timezone"):
        Loan(
            user_id=1,
            book_copy_id=1,
            checked_out_at=datetime(2026, 1, 1),
            due_at=datetime(2026, 1, 2),
        )


def test_fine_requires_positive_currency_precision() -> None:
    fine = Fine(user_id=1, reason="Overdue", amount=Decimal("10.50"))

    assert fine.amount == Decimal("10.50")

    with pytest.raises(DomainValidationError, match="two decimal"):
        Fine(user_id=1, reason="Overdue", amount=Decimal("10.505"))


def test_fine_status_requires_matching_settlement_timestamp() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(DomainValidationError, match="requires"):
        Fine(
            user_id=1,
            reason="Overdue",
            amount=Decimal("10.00"),
            status=FineStatus.PAID,
        )
    with pytest.raises(DomainValidationError, match="outstanding"):
        Fine(user_id=1, reason="Overdue", amount=Decimal("10.00"), settled_at=now)


def test_fine_settlement_normalizes_money_and_note() -> None:
    settlement = FineSettlement(
        fine_id=1,
        recorded_by_user_id=2,
        kind=FineSettlementKind.PAYMENT,
        amount=Decimal("10"),
        note="  Receipt 42  ",
    )

    assert settlement.amount == Decimal("10.00")
    assert settlement.note == "Receipt 42"


def test_return_cannot_precede_checkout() -> None:
    checkout = datetime(2026, 1, 2, tzinfo=UTC)

    with pytest.raises(DomainValidationError, match="precede"):
        Loan(
            user_id=1,
            book_copy_id=1,
            checked_out_at=checkout,
            due_at=checkout + timedelta(days=14),
            returned_at=checkout - timedelta(seconds=1),
        )


def test_reservation_resolution_state_matches_timestamp() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(DomainValidationError, match="active reservation"):
        Reservation(user_id=1, book_id=1, resolved_at=now)
    with pytest.raises(DomainValidationError, match="requires"):
        Reservation(
            user_id=1,
            book_id=1,
            status=ReservationStatus.CANCELLED,
        )


def test_loan_rejects_negative_renewal_count() -> None:
    checkout = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(DomainValidationError, match="Renewal count"):
        Loan(
            user_id=1,
            book_copy_id=1,
            checked_out_at=checkout,
            due_at=checkout + timedelta(days=14),
            renewal_count=-1,
        )


def test_book_request_state_requires_review_and_acquisition_metadata() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(DomainValidationError, match="reviewer"):
        BookRequest(
            user_id=1,
            title="Dune",
            author="Frank Herbert",
            status=RequestStatus.APPROVED,
        )
    with pytest.raises(DomainValidationError, match="requires a review note"):
        BookRequest(
            user_id=1,
            title="Dune",
            author="Frank Herbert",
            status=RequestStatus.REJECTED,
            reviewed_by_user_id=2,
            reviewed_at=now,
        )
    acquired = BookRequest(
        user_id=1,
        title="Dune",
        author="Frank Herbert",
        status=RequestStatus.ACQUIRED,
        reviewed_by_user_id=2,
        reviewed_at=now,
        acquired_book_id=3,
        acquired_by_user_id=2,
        acquired_at=now,
    )

    assert acquired.acquired_book_id == 3


def test_feedback_state_requires_matching_review_metadata() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(DomainValidationError, match="New feedback"):
        Feedback(content="More hours", user_id=1, reviewed_by_user_id=2, reviewed_at=now)
    reviewed = Feedback(
        content="More hours",
        user_id=1,
        status=FeedbackStatus.REVIEWED,
        reviewed_by_user_id=2,
        reviewed_at=now,
    )

    assert reviewed.status is FeedbackStatus.REVIEWED
