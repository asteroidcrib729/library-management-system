"""PostgreSQL acquisition-request and feedback repositories."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import psycopg
from psycopg import Connection

from library_management.domain import BookRequest, Feedback, FeedbackStatus, RequestStatus
from library_management.postgres.database import Row
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.postgres.common import (
    as_datetime,
    optional_datetime,
    returned_row,
)


class PostgresBookRequestRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, request: BookRequest) -> BookRequest:
        if request.id is not None:
            raise ValueError("A new book request cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO book_requests(
                        user_id, title, author, publication_year, status, created_at,
                        reviewed_by_user_id, reviewed_at, review_note, acquired_book_id,
                        acquired_by_user_id, acquired_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        request.user_id,
                        request.title,
                        request.author,
                        request.publication_year,
                        request.status.value,
                        request.created_at,
                        request.reviewed_by_user_id,
                        request.reviewed_at,
                        request.review_note,
                        request.acquired_book_id,
                        request.acquired_by_user_id,
                        request.acquired_at,
                    ),
                ),
                "book-request identifier",
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError("That pending book request already exists.") from error
        except psycopg.errors.ForeignKeyViolation as error:
            raise RecordNotFoundError("A referenced user or book was not found.") from error
        return replace(request, id=int(row["id"]))

    def get_by_id(self, request_id: int) -> BookRequest | None:
        row = self._connection.execute(
            "SELECT * FROM book_requests WHERE id=%s", (request_id,)
        ).fetchone()
        return self._map(row) if row else None

    def find_pending_duplicate(
        self, user_id: int, title: str, author: str, publication_year: int | None
    ) -> BookRequest | None:
        row = self._connection.execute(
            """
            SELECT * FROM book_requests
            WHERE user_id=%s AND status='pending'
              AND lower(trim(title))=lower(trim(%s))
              AND lower(trim(author))=lower(trim(%s))
              AND publication_year IS NOT DISTINCT FROM %s
            ORDER BY id LIMIT 1
            """,
            (user_id, title, author, publication_year),
        ).fetchone()
        return self._map(row) if row else None

    def list_for_user(self, user_id: int, status: RequestStatus | None = None) -> list[BookRequest]:
        if status is None:
            rows = self._connection.execute(
                """
                SELECT * FROM book_requests WHERE user_id=%s
                ORDER BY created_at DESC, id DESC
                """,
                (user_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM book_requests WHERE user_id=%s AND status=%s
                ORDER BY created_at DESC, id DESC
                """,
                (user_id, status.value),
            ).fetchall()
        return [self._map(row) for row in rows]

    def list_all(self, status: RequestStatus | None = None) -> list[BookRequest]:
        if status is None:
            rows = self._connection.execute(
                "SELECT * FROM book_requests ORDER BY created_at DESC, id DESC"
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM book_requests WHERE status=%s
                ORDER BY created_at DESC, id DESC
                """,
                (status.value,),
            ).fetchall()
        return [self._map(row) for row in rows]

    def review(
        self,
        request_id: int,
        status: RequestStatus,
        reviewed_by_user_id: int,
        reviewed_at: datetime,
        review_note: str | None,
    ) -> None:
        if status not in {RequestStatus.APPROVED, RequestStatus.REJECTED}:
            raise ValueError("Review status must be approved or rejected.")
        cursor = self._connection.execute(
            """
            UPDATE book_requests
            SET status=%s, reviewed_by_user_id=%s, reviewed_at=%s, review_note=%s
            WHERE id=%s AND status='pending'
            """,
            (status.value, reviewed_by_user_id, reviewed_at, review_note, request_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Pending book request {request_id} was not found.")

    def mark_acquired(
        self,
        request_id: int,
        book_id: int,
        acquired_by_user_id: int,
        acquired_at: datetime,
    ) -> None:
        cursor = self._connection.execute(
            """
            UPDATE book_requests
            SET status='acquired', acquired_book_id=%s, acquired_by_user_id=%s,
                acquired_at=%s
            WHERE id=%s AND status='approved'
            """,
            (book_id, acquired_by_user_id, acquired_at, request_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Approved book request {request_id} was not found.")

    @staticmethod
    def _map(row: Row) -> BookRequest:
        return BookRequest(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            title=str(row["title"]),
            author=str(row["author"]),
            publication_year=(
                int(row["publication_year"]) if row["publication_year"] is not None else None
            ),
            status=RequestStatus(str(row["status"])),
            created_at=as_datetime(row["created_at"]),
            reviewed_by_user_id=(
                int(row["reviewed_by_user_id"]) if row["reviewed_by_user_id"] is not None else None
            ),
            reviewed_at=optional_datetime(row["reviewed_at"]),
            review_note=str(row["review_note"]) if row["review_note"] is not None else None,
            acquired_book_id=(
                int(row["acquired_book_id"]) if row["acquired_book_id"] is not None else None
            ),
            acquired_by_user_id=(
                int(row["acquired_by_user_id"]) if row["acquired_by_user_id"] is not None else None
            ),
            acquired_at=optional_datetime(row["acquired_at"]),
        )


class PostgresFeedbackRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, feedback: Feedback) -> Feedback:
        if feedback.id is not None:
            raise ValueError("New feedback cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO feedback(user_id, content, created_at, status,
                                         reviewed_by_user_id, reviewed_at)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (
                        feedback.user_id,
                        feedback.content,
                        feedback.created_at,
                        feedback.status.value,
                        feedback.reviewed_by_user_id,
                        feedback.reviewed_at,
                    ),
                ),
                "feedback identifier",
            )
        except psycopg.errors.ForeignKeyViolation as error:
            raise RecordNotFoundError("The feedback user or reviewer was not found.") from error
        return replace(feedback, id=int(row["id"]))

    def get_by_id(self, feedback_id: int) -> Feedback | None:
        row = self._connection.execute(
            "SELECT * FROM feedback WHERE id=%s", (feedback_id,)
        ).fetchone()
        return self._map(row) if row else None

    def list_for_user(self, user_id: int, status: FeedbackStatus | None = None) -> list[Feedback]:
        if status is None:
            rows = self._connection.execute(
                "SELECT * FROM feedback WHERE user_id=%s ORDER BY created_at DESC, id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM feedback WHERE user_id=%s AND status=%s
                ORDER BY created_at DESC, id DESC
                """,
                (user_id, status.value),
            ).fetchall()
        return [self._map(row) for row in rows]

    def list_all(self, status: FeedbackStatus | None = None) -> list[Feedback]:
        if status is None:
            rows = self._connection.execute(
                "SELECT * FROM feedback ORDER BY created_at DESC, id DESC"
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM feedback WHERE status=%s ORDER BY created_at DESC, id DESC
                """,
                (status.value,),
            ).fetchall()
        return [self._map(row) for row in rows]

    def update_status(
        self,
        feedback_id: int,
        expected_status: FeedbackStatus,
        status: FeedbackStatus,
        reviewed_by_user_id: int,
        reviewed_at: datetime,
    ) -> None:
        cursor = self._connection.execute(
            """
            UPDATE feedback SET status=%s, reviewed_by_user_id=%s, reviewed_at=%s
            WHERE id=%s AND status=%s
            """,
            (status.value, reviewed_by_user_id, reviewed_at, feedback_id, expected_status.value),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(
                f"{expected_status.value.title()} feedback {feedback_id} was not found."
            )

    @staticmethod
    def _map(row: Row) -> Feedback:
        return Feedback(
            id=int(row["id"]),
            user_id=int(row["user_id"]) if row["user_id"] is not None else None,
            content=str(row["content"]),
            created_at=as_datetime(row["created_at"]),
            status=FeedbackStatus(str(row["status"])),
            reviewed_by_user_id=(
                int(row["reviewed_by_user_id"]) if row["reviewed_by_user_id"] is not None else None
            ),
            reviewed_at=optional_datetime(row["reviewed_at"]),
        )
