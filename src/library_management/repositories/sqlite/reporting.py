"""Read-only SQLite aggregate queries for recommendations and reporting."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal

from library_management.repositories.sqlite.mapping import to_database_datetime

MINOR_UNITS = Decimal("100")


class SqliteReportingRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def count_active_users(self) -> int:
        return self._count("SELECT count(*) FROM users WHERE is_active = 1")

    def count_titles(self) -> int:
        return self._count("SELECT count(*) FROM books")

    def count_copies(self) -> tuple[int, int]:
        row = self._connection.execute(
            """
            SELECT count(*) AS total,
                   coalesce(sum(CASE WHEN status = 'available' THEN 1 ELSE 0 END), 0)
                       AS available
            FROM book_copies
            """
        ).fetchone()
        return int(row["total"]), int(row["available"])

    def count_active_loans(self) -> int:
        return self._count("SELECT count(*) FROM loans WHERE returned_at IS NULL")

    def count_overdue_loans(self, now: datetime) -> int:
        return self._count(
            "SELECT count(*) FROM loans WHERE returned_at IS NULL AND due_at < ?",
            (to_database_datetime(now),),
        )

    def count_active_reservations(self) -> int:
        return self._count("SELECT count(*) FROM reservations WHERE status = 'active'")

    def outstanding_fines(self) -> tuple[int, Decimal]:
        row = self._connection.execute(
            """
            SELECT count(*) AS count, coalesce(sum(amount_minor), 0) AS amount_minor
            FROM fines WHERE status = 'outstanding'
            """
        ).fetchone()
        return int(row["count"]), Decimal(int(row["amount_minor"])) / MINOR_UNITS

    def count_pending_requests(self) -> int:
        return self._count("SELECT count(*) FROM book_requests WHERE status = 'pending'")

    def count_new_feedback(self) -> int:
        return self._count("SELECT count(*) FROM feedback WHERE status = 'new'")

    def loan_counts_by_book(self) -> dict[int, int]:
        rows = self._connection.execute(
            """
            SELECT book_copies.book_id AS book_id, count(loans.id) AS loan_count
            FROM loans
            JOIN book_copies ON book_copies.id = loans.book_copy_id
            GROUP BY book_copies.book_id
            """
        ).fetchall()
        return {int(row["book_id"]): int(row["loan_count"]) for row in rows}

    def _count(self, statement: str, parameters: tuple[str, ...] = ()) -> int:
        row = self._connection.execute(statement, parameters).fetchone()
        return int(row[0])
