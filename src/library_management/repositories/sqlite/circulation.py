"""SQLite reservation and loan repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime

from library_management.domain import Loan, Reservation, ReservationStatus
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.sqlite.mapping import (
    from_database_datetime,
    to_database_datetime,
)


class SqliteReservationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, reservation: Reservation) -> Reservation:
        if reservation.id is not None:
            raise ValueError("A new reservation cannot already have an identifier.")
        try:
            cursor = self._connection.execute(
                """
                INSERT INTO reservations(user_id, book_id, status, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    reservation.user_id,
                    reservation.book_id,
                    reservation.status.value,
                    to_database_datetime(reservation.created_at),
                    (
                        to_database_datetime(reservation.resolved_at)
                        if reservation.resolved_at is not None
                        else None
                    ),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError(
                "An active reservation for this user and book already exists."
            ) from error
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the reservation.")
        return replace(reservation, id=cursor.lastrowid)

    def get_by_id(self, reservation_id: int) -> Reservation | None:
        row = self._connection.execute(
            "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()
        return self._map(row) if row is not None else None

    def get_active_for_user_book(self, user_id: int, book_id: int) -> Reservation | None:
        row = self._connection.execute(
            """
            SELECT * FROM reservations
            WHERE user_id = ? AND book_id = ? AND status = 'active'
            """,
            (user_id, book_id),
        ).fetchone()
        return self._map(row) if row is not None else None

    def list_active_for_book(self, book_id: int) -> list[Reservation]:
        rows = self._connection.execute(
            """
            SELECT * FROM reservations
            WHERE book_id = ? AND status = 'active'
            ORDER BY created_at, id
            """,
            (book_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    def list_for_user(self, user_id: int) -> list[Reservation]:
        rows = self._connection.execute(
            """
            SELECT * FROM reservations
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    def resolve(
        self,
        reservation_id: int,
        status: ReservationStatus,
        resolved_at: datetime,
    ) -> None:
        if status is ReservationStatus.ACTIVE:
            raise ValueError("A resolved reservation cannot remain active.")
        cursor = self._connection.execute(
            """
            UPDATE reservations
            SET status = ?, resolved_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (status.value, to_database_datetime(resolved_at), reservation_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Active reservation {reservation_id} was not found.")

    @staticmethod
    def _map(row: sqlite3.Row) -> Reservation:
        resolved_value = row["resolved_at"]
        return Reservation(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            book_id=int(row["book_id"]),
            status=ReservationStatus(str(row["status"])),
            created_at=from_database_datetime(str(row["created_at"])),
            resolved_at=(
                from_database_datetime(str(resolved_value)) if resolved_value is not None else None
            ),
        )


class SqliteLoanRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, loan: Loan) -> Loan:
        if loan.id is not None:
            raise ValueError("A new loan cannot already have an identifier.")
        try:
            cursor = self._connection.execute(
                """
                INSERT INTO loans(
                    user_id, book_copy_id, checked_out_at, due_at, returned_at, renewal_count
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    loan.user_id,
                    loan.book_copy_id,
                    to_database_datetime(loan.checked_out_at),
                    to_database_datetime(loan.due_at),
                    (
                        to_database_datetime(loan.returned_at)
                        if loan.returned_at is not None
                        else None
                    ),
                    loan.renewal_count,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError("The copy already has an active loan.") from error
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the loan.")
        return replace(loan, id=cursor.lastrowid)

    def get_by_id(self, loan_id: int) -> Loan | None:
        row = self._connection.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        return self._map(row) if row is not None else None

    def get_active_by_copy(self, book_copy_id: int) -> Loan | None:
        row = self._connection.execute(
            "SELECT * FROM loans WHERE book_copy_id = ? AND returned_at IS NULL",
            (book_copy_id,),
        ).fetchone()
        return self._map(row) if row is not None else None

    def user_has_active_book(self, user_id: int, book_id: int) -> bool:
        row = self._connection.execute(
            """
            SELECT 1
            FROM loans
            JOIN book_copies ON book_copies.id = loans.book_copy_id
            WHERE loans.user_id = ? AND book_copies.book_id = ? AND loans.returned_at IS NULL
            LIMIT 1
            """,
            (user_id, book_id),
        ).fetchone()
        return row is not None

    def count_active_for_user(self, user_id: int) -> int:
        row = self._connection.execute(
            "SELECT count(*) AS count FROM loans WHERE user_id = ? AND returned_at IS NULL",
            (user_id,),
        ).fetchone()
        return int(row["count"])

    def list_for_user(self, user_id: int) -> list[Loan]:
        rows = self._connection.execute(
            """
            SELECT * FROM loans
            WHERE user_id = ?
            ORDER BY checked_out_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    def mark_returned(self, loan_id: int, returned_at: datetime) -> None:
        cursor = self._connection.execute(
            """
            UPDATE loans SET returned_at = ?
            WHERE id = ? AND returned_at IS NULL
            """,
            (to_database_datetime(returned_at), loan_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Active loan {loan_id} was not found.")

    def renew(self, loan_id: int, due_at: datetime, renewal_count: int) -> None:
        cursor = self._connection.execute(
            """
            UPDATE loans SET due_at = ?, renewal_count = ?
            WHERE id = ? AND returned_at IS NULL
            """,
            (to_database_datetime(due_at), renewal_count, loan_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Active loan {loan_id} was not found.")

    @staticmethod
    def _map(row: sqlite3.Row) -> Loan:
        returned_value = row["returned_at"]
        return Loan(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            book_copy_id=int(row["book_copy_id"]),
            checked_out_at=from_database_datetime(str(row["checked_out_at"])),
            due_at=from_database_datetime(str(row["due_at"])),
            returned_at=(
                from_database_datetime(str(returned_value)) if returned_value is not None else None
            ),
            renewal_count=int(row["renewal_count"]),
        )
