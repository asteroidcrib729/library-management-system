"""Read-only PostgreSQL aggregate queries."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import LiteralString

from psycopg import Connection

from library_management.postgres.database import Row
from library_management.repositories.postgres.common import returned_row

MINOR_UNITS = Decimal("100")


class PostgresReportingRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def count_active_users(self) -> int:
        return self._count("SELECT count(*) AS count FROM users WHERE is_active")

    def count_titles(self) -> int:
        return self._count("SELECT count(*) AS count FROM books")

    def count_copies(self) -> tuple[int, int]:
        row = returned_row(
            self._connection.execute(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE status='available') AS available
                FROM book_copies
                """
            ),
            "copy counts",
        )
        return int(row["total"]), int(row["available"])

    def count_active_loans(self) -> int:
        return self._count("SELECT count(*) AS count FROM loans WHERE returned_at IS NULL")

    def count_overdue_loans(self, now: datetime) -> int:
        return self._count(
            "SELECT count(*) AS count FROM loans WHERE returned_at IS NULL AND due_at < %s",
            (now,),
        )

    def count_active_reservations(self) -> int:
        return self._count("SELECT count(*) AS count FROM reservations WHERE status='active'")

    def outstanding_fines(self) -> tuple[int, Decimal]:
        row = returned_row(
            self._connection.execute(
                """
                SELECT count(*) AS count, coalesce(sum(amount_minor), 0) AS amount
                FROM fines WHERE status='outstanding'
                """
            ),
            "fine totals",
        )
        return int(row["count"]), Decimal(int(row["amount"])) / MINOR_UNITS

    def count_pending_requests(self) -> int:
        return self._count("SELECT count(*) AS count FROM book_requests WHERE status='pending'")

    def count_new_feedback(self) -> int:
        return self._count("SELECT count(*) AS count FROM feedback WHERE status='new'")

    def loan_counts_by_book(self) -> dict[int, int]:
        rows = self._connection.execute(
            """
            SELECT book_copies.book_id, count(*) AS count
            FROM loans JOIN book_copies ON book_copies.id=loans.book_copy_id
            GROUP BY book_copies.book_id
            """
        ).fetchall()
        return {int(row["book_id"]): int(row["count"]) for row in rows}

    def _count(self, statement: LiteralString, parameters: tuple[object, ...] = ()) -> int:
        row = returned_row(self._connection.execute(statement, parameters), "count")
        return int(row["count"])
