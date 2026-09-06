"""Book acquisition request and feedback application workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from library_management.domain import (
    BookRequest,
    Feedback,
    FeedbackStatus,
    RequestStatus,
    User,
    UserRole,
)
from library_management.repositories import DuplicateRecordError, RecordNotFoundError, UnitOfWork
from library_management.services.accounts import UnitOfWorkFactory
from library_management.services.authorization import require_active_user, require_role
from library_management.services.errors import (
    EngagementNotFoundError,
    InvalidSubmissionTransitionError,
    SubmissionConflictError,
)

Clock = Callable[[], datetime]
ENGAGEMENT_STAFF_ROLES = frozenset({UserRole.LIBRARIAN, UserRole.ADMINISTRATOR})


def system_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class BookRequestView:
    request: BookRequest
    username: str
    reviewer_username: str | None = None
    acquired_book_title: str | None = None
    acquisition_actor_username: str | None = None


@dataclass(frozen=True, slots=True)
class FeedbackView:
    feedback: Feedback
    username: str
    reviewer_username: str | None = None


class EngagementService:
    """Manage member submissions and staff review lifecycles."""

    def __init__(
        self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock = system_clock
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def submit_book_request(
        self,
        actor_id: int,
        title: str,
        author: str,
        publication_year: int | None = None,
    ) -> BookRequestView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.lock_rows(users=(actor_id,))
            actor = require_active_user(unit_of_work, actor_id)
            if actor.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            request = BookRequest(
                user_id=actor.id,
                title=title,
                author=author,
                publication_year=publication_year,
                created_at=now,
            )
            duplicate = unit_of_work.book_requests.find_pending_duplicate(
                actor.id, request.title, request.author, request.publication_year
            )
            if duplicate is not None:
                raise SubmissionConflictError("You already have a pending request for this book.")
            try:
                saved = unit_of_work.book_requests.add(request)
            except DuplicateRecordError as error:
                raise SubmissionConflictError(
                    "You already have a pending request for this book."
                ) from error
            unit_of_work.commit()
        return BookRequestView(saved, actor.username)

    def list_book_requests(
        self,
        actor_id: int,
        status: RequestStatus | None = None,
    ) -> list[BookRequestView]:
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_active_user(unit_of_work, actor_id)
            if actor.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            requests = (
                unit_of_work.book_requests.list_all(status)
                if actor.role in ENGAGEMENT_STAFF_ROLES
                else unit_of_work.book_requests.list_for_user(actor.id, status)
            )
            return [self._request_view(unit_of_work, request) for request in requests]

    def review_book_request(
        self,
        actor_id: int,
        request_id: int,
        status: RequestStatus,
        note: str | None = None,
    ) -> BookRequestView:
        if status not in {RequestStatus.APPROVED, RequestStatus.REJECTED}:
            raise InvalidSubmissionTransitionError(
                "A review decision must be approved or rejected."
            )
        cleaned_note = note.strip() if note is not None else ""
        if status is RequestStatus.REJECTED and not cleaned_note:
            raise InvalidSubmissionTransitionError("A rejection note is required.")
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_role(
                unit_of_work,
                actor_id,
                ENGAGEMENT_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            request = self._get_request(unit_of_work, request_id)
            unit_of_work.lock_rows(users=(actor_id, request.user_id), book_requests=(request_id,))
            actor = require_role(
                unit_of_work,
                actor_id,
                ENGAGEMENT_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            request = self._get_request(unit_of_work, request_id)
            if request.status is not RequestStatus.PENDING:
                raise InvalidSubmissionTransitionError("Only a pending request can be reviewed.")
            if actor.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            try:
                unit_of_work.book_requests.review(
                    request_id,
                    status,
                    actor.id,
                    now,
                    cleaned_note or None,
                )
            except RecordNotFoundError as error:
                raise InvalidSubmissionTransitionError(
                    "Only a pending request can be reviewed."
                ) from error
            owner_username = self._owner_username(request, unit_of_work)
            unit_of_work.commit()
        reviewed = replace(
            request,
            status=status,
            reviewed_by_user_id=actor.id,
            reviewed_at=now,
            review_note=cleaned_note or None,
        )
        return BookRequestView(reviewed, owner_username, actor.username)

    def mark_request_acquired(
        self,
        actor_id: int,
        request_id: int,
        book_id: int,
    ) -> BookRequestView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_role(
                unit_of_work,
                actor_id,
                ENGAGEMENT_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            request = self._get_request(unit_of_work, request_id)
            unit_of_work.lock_rows(
                users=(actor_id, request.user_id),
                books=(book_id,),
                book_requests=(request_id,),
            )
            actor = require_role(
                unit_of_work,
                actor_id,
                ENGAGEMENT_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            request = self._get_request(unit_of_work, request_id)
            if request.status is not RequestStatus.APPROVED:
                raise InvalidSubmissionTransitionError(
                    "Only an approved request can be marked acquired."
                )
            book = unit_of_work.books.get_by_id(book_id)
            if book is None:
                raise EngagementNotFoundError(f"Book {book_id} was not found.")
            if actor.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            try:
                unit_of_work.book_requests.mark_acquired(request_id, book_id, actor.id, now)
            except RecordNotFoundError as error:
                raise InvalidSubmissionTransitionError(
                    "Only an approved request can be marked acquired."
                ) from error
            owner = self._get_user(unit_of_work, request.user_id)
            reviewer_username = self._optional_username(unit_of_work, request.reviewed_by_user_id)
            unit_of_work.commit()
        acquired = replace(
            request,
            status=RequestStatus.ACQUIRED,
            acquired_book_id=book_id,
            acquired_by_user_id=actor.id,
            acquired_at=now,
        )
        return BookRequestView(
            acquired,
            owner.username,
            reviewer_username,
            book.title,
            actor.username,
        )

    def submit_feedback(self, actor_id: int, content: str) -> FeedbackView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.lock_rows(users=(actor_id,))
            actor = require_active_user(unit_of_work, actor_id)
            if actor.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            saved = unit_of_work.feedback.add(
                Feedback(user_id=actor.id, content=content, created_at=now)
            )
            unit_of_work.commit()
        return FeedbackView(saved, actor.username)

    def list_feedback(
        self,
        actor_id: int,
        status: FeedbackStatus | None = None,
    ) -> list[FeedbackView]:
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_active_user(unit_of_work, actor_id)
            if actor.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            feedback_items = (
                unit_of_work.feedback.list_all(status)
                if actor.role in ENGAGEMENT_STAFF_ROLES
                else unit_of_work.feedback.list_for_user(actor.id, status)
            )
            return [self._feedback_view(unit_of_work, item) for item in feedback_items]

    def review_feedback(self, actor_id: int, feedback_id: int) -> FeedbackView:
        return self._transition_feedback(
            actor_id, feedback_id, FeedbackStatus.NEW, FeedbackStatus.REVIEWED
        )

    def archive_feedback(self, actor_id: int, feedback_id: int) -> FeedbackView:
        return self._transition_feedback(
            actor_id, feedback_id, FeedbackStatus.REVIEWED, FeedbackStatus.ARCHIVED
        )

    def _transition_feedback(
        self,
        actor_id: int,
        feedback_id: int,
        expected_status: FeedbackStatus,
        status: FeedbackStatus,
    ) -> FeedbackView:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_role(
                unit_of_work,
                actor_id,
                ENGAGEMENT_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            feedback = self._get_feedback(unit_of_work, feedback_id)
            user_ids = (actor_id,) if feedback.user_id is None else (actor_id, feedback.user_id)
            unit_of_work.lock_rows(users=user_ids, feedback=(feedback_id,))
            actor = require_role(
                unit_of_work,
                actor_id,
                ENGAGEMENT_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            feedback = self._get_feedback(unit_of_work, feedback_id)
            if feedback.status is not expected_status:
                raise InvalidSubmissionTransitionError(
                    f"Only {expected_status.value} feedback can be marked {status.value}."
                )
            if actor.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            try:
                unit_of_work.feedback.update_status(
                    feedback_id, expected_status, status, actor.id, now
                )
            except RecordNotFoundError as error:
                raise InvalidSubmissionTransitionError(
                    f"Only {expected_status.value} feedback can be marked {status.value}."
                ) from error
            owner_username = self._feedback_owner_username(unit_of_work, feedback)
            unit_of_work.commit()
        updated = replace(
            feedback,
            status=status,
            reviewed_by_user_id=actor.id,
            reviewed_at=now,
        )
        return FeedbackView(updated, owner_username, actor.username)

    def _request_view(self, unit_of_work: UnitOfWork, request: BookRequest) -> BookRequestView:
        book_title = None
        if request.acquired_book_id is not None:
            book = unit_of_work.books.get_by_id(request.acquired_book_id)
            book_title = book.title if book is not None else None
        return BookRequestView(
            request,
            self._owner_username(request, unit_of_work),
            self._optional_username(unit_of_work, request.reviewed_by_user_id),
            book_title,
            self._optional_username(unit_of_work, request.acquired_by_user_id),
        )

    def _feedback_view(self, unit_of_work: UnitOfWork, feedback: Feedback) -> FeedbackView:
        return FeedbackView(
            feedback,
            self._feedback_owner_username(unit_of_work, feedback),
            self._optional_username(unit_of_work, feedback.reviewed_by_user_id),
        )

    @staticmethod
    def _owner_username(request: BookRequest, unit_of_work: UnitOfWork) -> str:
        user = unit_of_work.users.get_by_id(request.user_id)
        return user.username if user is not None else "<deleted account>"

    @staticmethod
    def _feedback_owner_username(unit_of_work: UnitOfWork, feedback: Feedback) -> str:
        if feedback.user_id is None:
            return "<anonymous>"
        user = unit_of_work.users.get_by_id(feedback.user_id)
        return user.username if user is not None else "<deleted account>"

    @staticmethod
    def _optional_username(unit_of_work: UnitOfWork, user_id: int | None) -> str | None:
        if user_id is None:
            return None
        user = unit_of_work.users.get_by_id(user_id)
        return user.username if user is not None else "<deleted account>"

    @staticmethod
    def _get_request(unit_of_work: UnitOfWork, request_id: int) -> BookRequest:
        request = unit_of_work.book_requests.get_by_id(request_id)
        if request is None:
            raise EngagementNotFoundError(f"Book request {request_id} was not found.")
        return request

    @staticmethod
    def _get_feedback(unit_of_work: UnitOfWork, feedback_id: int) -> Feedback:
        feedback = unit_of_work.feedback.get_by_id(feedback_id)
        if feedback is None:
            raise EngagementNotFoundError(f"Feedback {feedback_id} was not found.")
        return feedback

    @staticmethod
    def _get_user(unit_of_work: UnitOfWork, user_id: int) -> User:
        user = unit_of_work.users.get_by_id(user_id)
        if user is None:
            raise EngagementNotFoundError(f"User {user_id} was not found.")
        return user

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Engagement clock must return a timezone-aware timestamp.")
        return value.astimezone(UTC)
