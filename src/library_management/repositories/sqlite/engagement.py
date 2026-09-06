"""SQLite book-request and feedback repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime

from library_management.domain import (
    BookRequest,
    Feedback,
    FeedbackStatus,
    RequestStatus,
)
from library_management.repositories.errors import RecordNotFoundError
from library_management.repositories.sqlite.mapping import (
    from_database_datetime,
    to_database_datetime,
)


class SqliteBookRequestRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, request: BookRequest) -> BookRequest:
        if request.id is not None:
            raise ValueError("A new book request cannot already have an identifier.")
        cursor = self._connection.execute(
            """
            INSERT INTO book_requests(
                user_id, title, author, publication_year, status, created_at,
                reviewed_by_user_id, reviewed_at, review_note, acquired_book_id,
                acquired_by_user_id, acquired_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.user_id,
                request.title,
                request.author,
                request.publication_year,
                request.status.value,
                to_database_datetime(request.created_at),
                request.reviewed_by_user_id,
                self._optional_datetime(request.reviewed_at),
                request.review_note,
                request.acquired_book_id,
                request.acquired_by_user_id,
                self._optional_datetime(request.acquired_at),
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the book request.")
        return replace(request, id=cursor.lastrowid)

    def get_by_id(self, request_id: int) -> BookRequest | None:
        row = self._connection.execute(
            "SELECT * FROM book_requests WHERE id = ?", (request_id,)
        ).fetchone()
        return self._map(row) if row is not None else None

    def find_pending_duplicate(
        self, user_id: int, title: str, author: str, publication_year: int | None
    ) -> BookRequest | None:
        row = self._connection.execute(
            """
            SELECT * FROM book_requests
            WHERE user_id = ? AND status = 'pending'
              AND lower(trim(title)) = lower(trim(?))
              AND lower(trim(author)) = lower(trim(?))
              AND publication_year IS ?
            ORDER BY id LIMIT 1
            """,
            (user_id, title, author, publication_year),
        ).fetchone()
        return self._map(row) if row is not None else None

    def list_for_user(self, user_id: int, status: RequestStatus | None = None) -> list[BookRequest]:
        if status is None:
            rows = self._connection.execute(
                "SELECT * FROM book_requests WHERE user_id = ? ORDER BY created_at DESC, id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM book_requests
                WHERE user_id = ? AND status = ? ORDER BY created_at DESC, id DESC
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
                SELECT * FROM book_requests
                WHERE status = ? ORDER BY created_at DESC, id DESC
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
            SET status = ?, reviewed_by_user_id = ?, reviewed_at = ?, review_note = ?
            WHERE id = ? AND status = 'pending'
            """,
            (
                status.value,
                reviewed_by_user_id,
                to_database_datetime(reviewed_at),
                review_note,
                request_id,
            ),
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
            SET status = 'acquired', acquired_book_id = ?, acquired_by_user_id = ?, acquired_at = ?
            WHERE id = ? AND status = 'approved'
            """,
            (book_id, acquired_by_user_id, to_database_datetime(acquired_at), request_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Approved book request {request_id} was not found.")

    @staticmethod
    def _optional_datetime(value: datetime | None) -> str | None:
        return to_database_datetime(value) if value is not None else None

    @staticmethod
    def _map(row: sqlite3.Row) -> BookRequest:
        reviewed_at = row["reviewed_at"]
        acquired_at = row["acquired_at"]
        return BookRequest(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            title=str(row["title"]),
            author=str(row["author"]),
            publication_year=(
                int(row["publication_year"]) if row["publication_year"] is not None else None
            ),
            status=RequestStatus(str(row["status"])),
            created_at=from_database_datetime(str(row["created_at"])),
            reviewed_by_user_id=(
                int(row["reviewed_by_user_id"]) if row["reviewed_by_user_id"] is not None else None
            ),
            reviewed_at=(
                from_database_datetime(str(reviewed_at)) if reviewed_at is not None else None
            ),
            review_note=str(row["review_note"]) if row["review_note"] is not None else None,
            acquired_book_id=(
                int(row["acquired_book_id"]) if row["acquired_book_id"] is not None else None
            ),
            acquired_by_user_id=(
                int(row["acquired_by_user_id"]) if row["acquired_by_user_id"] is not None else None
            ),
            acquired_at=(
                from_database_datetime(str(acquired_at)) if acquired_at is not None else None
            ),
        )


class SqliteFeedbackRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, feedback: Feedback) -> Feedback:
        if feedback.id is not None:
            raise ValueError("New feedback cannot already have an identifier.")
        cursor = self._connection.execute(
            """
            INSERT INTO feedback(
                user_id, content, created_at, status, reviewed_by_user_id, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                feedback.user_id,
                feedback.content,
                to_database_datetime(feedback.created_at),
                feedback.status.value,
                feedback.reviewed_by_user_id,
                (
                    to_database_datetime(feedback.reviewed_at)
                    if feedback.reviewed_at is not None
                    else None
                ),
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for feedback.")
        return replace(feedback, id=cursor.lastrowid)

    def get_by_id(self, feedback_id: int) -> Feedback | None:
        row = self._connection.execute(
            "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
        ).fetchone()
        return self._map(row) if row is not None else None

    def list_for_user(self, user_id: int, status: FeedbackStatus | None = None) -> list[Feedback]:
        if status is None:
            rows = self._connection.execute(
                "SELECT * FROM feedback WHERE user_id = ? ORDER BY created_at DESC, id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM feedback
                WHERE user_id = ? AND status = ? ORDER BY created_at DESC, id DESC
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
                "SELECT * FROM feedback WHERE status = ? ORDER BY created_at DESC, id DESC",
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
            UPDATE feedback SET status = ?, reviewed_by_user_id = ?, reviewed_at = ?
            WHERE id = ? AND status = ?
            """,
            (
                status.value,
                reviewed_by_user_id,
                to_database_datetime(reviewed_at),
                feedback_id,
                expected_status.value,
            ),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(
                f"{expected_status.value.title()} feedback {feedback_id} was not found."
            )

    @staticmethod
    def _map(row: sqlite3.Row) -> Feedback:
        reviewed_at = row["reviewed_at"]
        return Feedback(
            id=int(row["id"]),
            user_id=int(row["user_id"]) if row["user_id"] is not None else None,
            content=str(row["content"]),
            created_at=from_database_datetime(str(row["created_at"])),
            status=FeedbackStatus(str(row["status"])),
            reviewed_by_user_id=(
                int(row["reviewed_by_user_id"]) if row["reviewed_by_user_id"] is not None else None
            ),
            reviewed_at=(
                from_database_datetime(str(reviewed_at)) if reviewed_at is not None else None
            ),
        )
