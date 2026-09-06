from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial

import pytest

from library_management.database import Database
from library_management.domain import Book, FeedbackStatus, RequestStatus, User, UserRole
from library_management.repositories import UnitOfWork
from library_management.repositories.sqlite import SqliteUnitOfWork
from library_management.services import (
    AuthorizationError,
    EngagementNotFoundError,
    EngagementService,
    InvalidSubmissionTransitionError,
    SubmissionConflictError,
)

NOW = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


def build_factory(database: Database) -> Callable[[], UnitOfWork]:
    return partial(SqliteUnitOfWork, database)


def build_service(database: Database) -> EngagementService:
    return EngagementService(build_factory(database), clock=lambda: NOW)


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


def add_book(database: Database) -> Book:
    with SqliteUnitOfWork(database) as unit_of_work:
        book = unit_of_work.books.add(
            Book(title="Dune", author="Frank Herbert", publication_year=1965)
        )
        unit_of_work.commit()
    return book


def test_member_submits_request_and_duplicate_pending_is_rejected(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")

    submitted = service.submit_book_request(
        member.id or 0, "  Dune Messiah ", " Frank Herbert ", 1969
    )

    assert submitted.request.title == "Dune Messiah"
    assert submitted.request.status is RequestStatus.PENDING
    with pytest.raises(SubmissionConflictError, match="already have"):
        service.submit_book_request(member.id or 0, "dune messiah", "FRANK HERBERT", 1969)


def test_members_see_only_their_submissions_while_staff_can_filter(database: Database) -> None:
    service = build_service(database)
    first = add_user(database, "reader.one")
    second = add_user(database, "reader.two")
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    service.submit_book_request(first.id or 0, "Dune Messiah", "Frank Herbert", 1969)
    service.submit_book_request(second.id or 0, "Foundation", "Isaac Asimov", 1951)

    own = service.list_book_requests(first.id or 0)
    all_pending = service.list_book_requests(librarian.id or 0, RequestStatus.PENDING)

    assert [view.username for view in own] == [first.username]
    assert {view.username for view in all_pending} == {first.username, second.username}


def test_staff_reviews_request_and_rejection_requires_note(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    submitted = service.submit_book_request(member.id or 0, "Foundation", "Isaac Asimov")

    with pytest.raises(InvalidSubmissionTransitionError, match="note"):
        service.review_book_request(
            librarian.id or 0, submitted.request.id or 0, RequestStatus.REJECTED
        )

    rejected = service.review_book_request(
        librarian.id or 0,
        submitted.request.id or 0,
        RequestStatus.REJECTED,
        "Already ordered",
    )

    assert rejected.request.reviewed_at == NOW
    assert rejected.reviewer_username == librarian.username
    assert rejected.request.review_note == "Already ordered"
    with pytest.raises(InvalidSubmissionTransitionError, match="pending"):
        service.review_book_request(
            librarian.id or 0, submitted.request.id or 0, RequestStatus.APPROVED
        )


def test_approved_request_can_be_linked_to_catalog_once(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    submitted = service.submit_book_request(member.id or 0, "Dune", "Frank Herbert", 1965)
    service.review_book_request(
        librarian.id or 0, submitted.request.id or 0, RequestStatus.APPROVED
    )
    book = add_book(database)

    acquired = service.mark_request_acquired(
        librarian.id or 0, submitted.request.id or 0, book.id or 0
    )

    assert acquired.request.status is RequestStatus.ACQUIRED
    assert acquired.request.acquired_at == NOW
    assert acquired.acquired_book_title == book.title
    with pytest.raises(InvalidSubmissionTransitionError, match="approved"):
        service.mark_request_acquired(librarian.id or 0, submitted.request.id or 0, book.id or 0)


def test_acquisition_requires_existing_catalog_book(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    submitted = service.submit_book_request(member.id or 0, "Dune", "Frank Herbert")
    service.review_book_request(
        librarian.id or 0, submitted.request.id or 0, RequestStatus.APPROVED
    )

    with pytest.raises(EngagementNotFoundError, match="Book 999"):
        service.mark_request_acquired(librarian.id or 0, submitted.request.id or 0, 999)


def test_feedback_submission_visibility_and_lifecycle(database: Database) -> None:
    service = build_service(database)
    first = add_user(database, "reader.one")
    second = add_user(database, "reader.two")
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    submitted = service.submit_feedback(first.id or 0, "  Please extend weekend hours.  ")
    service.submit_feedback(second.id or 0, "Add more science fiction.")

    own = service.list_feedback(first.id or 0)
    reviewed = service.review_feedback(librarian.id or 0, submitted.feedback.id or 0)
    archived = service.archive_feedback(librarian.id or 0, submitted.feedback.id or 0)

    assert [view.username for view in own] == [first.username]
    assert own[0].feedback.content == "Please extend weekend hours."
    assert reviewed.feedback.status is FeedbackStatus.REVIEWED
    assert archived.feedback.status is FeedbackStatus.ARCHIVED
    assert archived.reviewer_username == librarian.username
    assert len(service.list_feedback(librarian.id or 0)) == 2


def test_members_cannot_review_requests_or_feedback(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    request = service.submit_book_request(member.id or 0, "Dune", "Frank Herbert")
    feedback = service.submit_feedback(member.id or 0, "More copies")

    with pytest.raises(AuthorizationError):
        service.review_book_request(member.id or 0, request.request.id or 0, RequestStatus.APPROVED)
    with pytest.raises(AuthorizationError):
        service.review_feedback(member.id or 0, feedback.feedback.id or 0)


def test_invalid_feedback_transition_preserves_state(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    submitted = service.submit_feedback(member.id or 0, "More copies")

    with pytest.raises(InvalidSubmissionTransitionError, match="reviewed feedback"):
        service.archive_feedback(librarian.id or 0, submitted.feedback.id or 0)

    stored = service.list_feedback(member.id or 0)
    assert stored[0].feedback.status is FeedbackStatus.NEW
