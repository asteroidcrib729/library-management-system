"""PostgreSQL reservation and loan repositories."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import psycopg
from psycopg import Connection

from library_management.domain import Loan, Reservation, ReservationStatus
from library_management.postgres.database import Row
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.postgres.common import (
    as_datetime,
    optional_datetime,
    returned_row,
)


class PostgresReservationRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, reservation: Reservation) -> Reservation:
        if reservation.id is not None:
            raise ValueError("A new reservation cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO reservations(user_id, book_id, status, created_at, resolved_at)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """,
                    (
                        reservation.user_id,
                        reservation.book_id,
                        reservation.status.value,
                        reservation.created_at,
                        reservation.resolved_at,
                    ),
                ),
                "reservation identifier",
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError(
                "An active reservation for this user and book already exists."
            ) from error
        except psycopg.errors.ForeignKeyViolation as error:
            raise RecordNotFoundError("The reservation user or book was not found.") from error
        return replace(reservation, id=int(row["id"]))

    def get_by_id(self, reservation_id: int) -> Reservation | None:
        row = self._connection.execute(
            "SELECT * FROM reservations WHERE id = %s", (reservation_id,)
        ).fetchone()
        return self._map(row) if row else None

    def get_active_for_user_book(self, user_id: int, book_id: int) -> Reservation | None:
        row = self._connection.execute(
            """
            SELECT * FROM reservations
            WHERE user_id = %s AND book_id = %s AND status = 'active'
            """,
            (user_id, book_id),
        ).fetchone()
        return self._map(row) if row else None

    def list_active_for_book(self, book_id: int) -> list[Reservation]:
        rows = self._connection.execute(
            """
            SELECT * FROM reservations WHERE book_id = %s AND status = 'active'
            ORDER BY created_at, id
            """,
            (book_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    def list_for_user(self, user_id: int) -> list[Reservation]:
        rows = self._connection.execute(
            "SELECT * FROM reservations WHERE user_id = %s ORDER BY created_at DESC, id DESC",
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
            UPDATE reservations SET status = %s, resolved_at = %s
            WHERE id = %s AND status = 'active'
            """,
            (status.value, resolved_at, reservation_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Active reservation {reservation_id} was not found.")

    @staticmethod
    def _map(row: Row) -> Reservation:
        return Reservation(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            book_id=int(row["book_id"]),
            status=ReservationStatus(str(row["status"])),
            created_at=as_datetime(row["created_at"]),
            resolved_at=optional_datetime(row["resolved_at"]),
        )


class PostgresLoanRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, loan: Loan) -> Loan:
        if loan.id is not None:
            raise ValueError("A new loan cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO loans(user_id, book_copy_id, checked_out_at, due_at,
                                      returned_at, renewal_count)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (
                        loan.user_id,
                        loan.book_copy_id,
                        loan.checked_out_at,
                        loan.due_at,
                        loan.returned_at,
                        loan.renewal_count,
                    ),
                ),
                "loan identifier",
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError("The copy already has an active loan.") from error
        except psycopg.errors.ForeignKeyViolation as error:
            raise RecordNotFoundError("The loan user or copy was not found.") from error
        return replace(loan, id=int(row["id"]))

    def get_by_id(self, loan_id: int) -> Loan | None:
        row = self._connection.execute("SELECT * FROM loans WHERE id = %s", (loan_id,)).fetchone()
        return self._map(row) if row else None

    def get_active_by_copy(self, book_copy_id: int) -> Loan | None:
        row = self._connection.execute(
            "SELECT * FROM loans WHERE book_copy_id = %s AND returned_at IS NULL",
            (book_copy_id,),
        ).fetchone()
        return self._map(row) if row else None

    def user_has_active_book(self, user_id: int, book_id: int) -> bool:
        return (
            self._connection.execute(
                """
                SELECT 1 FROM loans JOIN book_copies ON book_copies.id=loans.book_copy_id
                WHERE loans.user_id=%s AND book_copies.book_id=%s
                  AND loans.returned_at IS NULL LIMIT 1
                """,
                (user_id, book_id),
            ).fetchone()
            is not None
        )

    def count_active_for_user(self, user_id: int) -> int:
        row = returned_row(
            self._connection.execute(
                "SELECT count(*) AS count FROM loans WHERE user_id=%s AND returned_at IS NULL",
                (user_id,),
            ),
            "loan count",
        )
        return int(row["count"])

    def list_for_user(self, user_id: int) -> list[Loan]:
        rows = self._connection.execute(
            "SELECT * FROM loans WHERE user_id=%s ORDER BY checked_out_at DESC, id DESC",
            (user_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    def mark_returned(self, loan_id: int, returned_at: datetime) -> None:
        cursor = self._connection.execute(
            "UPDATE loans SET returned_at=%s WHERE id=%s AND returned_at IS NULL",
            (returned_at, loan_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Active loan {loan_id} was not found.")

    def renew(self, loan_id: int, due_at: datetime, renewal_count: int) -> None:
        cursor = self._connection.execute(
            """
            UPDATE loans SET due_at=%s, renewal_count=%s
            WHERE id=%s AND returned_at IS NULL AND renewal_count < %s
            """,
            (due_at, renewal_count, loan_id, renewal_count),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Active loan {loan_id} was not found.")

    @staticmethod
    def _map(row: Row) -> Loan:
        return Loan(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            book_copy_id=int(row["book_copy_id"]),
            checked_out_at=as_datetime(row["checked_out_at"]),
            due_at=as_datetime(row["due_at"]),
            returned_at=optional_datetime(row["returned_at"]),
            renewal_count=int(row["renewal_count"]),
        )
