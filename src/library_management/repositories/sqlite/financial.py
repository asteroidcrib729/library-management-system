"""SQLite fine and immutable settlement repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from library_management.domain import Fine, FineSettlement, FineSettlementKind, FineStatus
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.sqlite.mapping import (
    from_database_datetime,
    to_database_datetime,
)

MINOR_UNITS = Decimal("100")


def _to_minor_units(amount: Decimal) -> int:
    return int(amount * MINOR_UNITS)


def _from_minor_units(amount: int) -> Decimal:
    return Decimal(amount) / MINOR_UNITS


class SqliteFineRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, fine: Fine) -> Fine:
        if fine.id is not None:
            raise ValueError("A new fine cannot already have an identifier.")
        try:
            cursor = self._connection.execute(
                """
                INSERT INTO fines(
                    user_id, loan_id, reason, amount_minor, status, assessed_at, settled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fine.user_id,
                    fine.loan_id,
                    fine.reason,
                    _to_minor_units(fine.amount),
                    fine.status.value,
                    to_database_datetime(fine.assessed_at),
                    (
                        to_database_datetime(fine.settled_at)
                        if fine.settled_at is not None
                        else None
                    ),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError("The fine could not be created.") from error
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the fine.")
        return replace(fine, id=cursor.lastrowid)

    def get_by_id(self, fine_id: int) -> Fine | None:
        row = self._connection.execute("SELECT * FROM fines WHERE id = ?", (fine_id,)).fetchone()
        return self._map(row) if row is not None else None

    def get_by_loan_id(self, loan_id: int) -> Fine | None:
        row = self._connection.execute(
            "SELECT * FROM fines WHERE loan_id = ? ORDER BY id LIMIT 1", (loan_id,)
        ).fetchone()
        return self._map(row) if row is not None else None

    def list_for_user(self, user_id: int) -> list[Fine]:
        rows = self._connection.execute(
            "SELECT * FROM fines WHERE user_id = ? ORDER BY assessed_at DESC, id DESC",
            (user_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    def settle(self, fine_id: int, status: FineStatus, settled_at: datetime) -> None:
        if status is FineStatus.OUTSTANDING:
            raise ValueError("Settlement status cannot be outstanding.")
        cursor = self._connection.execute(
            """
            UPDATE fines SET status = ?, settled_at = ?
            WHERE id = ? AND status = 'outstanding'
            """,
            (status.value, to_database_datetime(settled_at), fine_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Outstanding fine {fine_id} was not found.")

    @staticmethod
    def _map(row: sqlite3.Row) -> Fine:
        settled_value = row["settled_at"]
        loan_value = row["loan_id"]
        return Fine(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            loan_id=int(loan_value) if loan_value is not None else None,
            reason=str(row["reason"]),
            amount=_from_minor_units(int(row["amount_minor"])),
            status=FineStatus(str(row["status"])),
            assessed_at=from_database_datetime(str(row["assessed_at"])),
            settled_at=(
                from_database_datetime(str(settled_value)) if settled_value is not None else None
            ),
        )


class SqliteFineSettlementRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, settlement: FineSettlement) -> FineSettlement:
        if settlement.id is not None:
            raise ValueError("A new settlement cannot already have an identifier.")
        try:
            cursor = self._connection.execute(
                """
                INSERT INTO fine_settlements(
                    fine_id, recorded_by_user_id, kind, amount_minor, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    settlement.fine_id,
                    settlement.recorded_by_user_id,
                    settlement.kind.value,
                    _to_minor_units(settlement.amount),
                    settlement.note,
                    to_database_datetime(settlement.created_at),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError("This fine already has a settlement record.") from error
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the settlement.")
        return replace(settlement, id=cursor.lastrowid)

    def get_for_fine(self, fine_id: int) -> FineSettlement | None:
        row = self._connection.execute(
            "SELECT * FROM fine_settlements WHERE fine_id = ?", (fine_id,)
        ).fetchone()
        return self._map(row) if row is not None else None

    def list_for_user(self, user_id: int) -> list[FineSettlement]:
        rows = self._connection.execute(
            """
            SELECT fine_settlements.* FROM fine_settlements
            JOIN fines ON fines.id = fine_settlements.fine_id
            WHERE fines.user_id = ?
            ORDER BY fine_settlements.created_at DESC, fine_settlements.id DESC
            """,
            (user_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: sqlite3.Row) -> FineSettlement:
        note_value = row["note"]
        return FineSettlement(
            id=int(row["id"]),
            fine_id=int(row["fine_id"]),
            recorded_by_user_id=int(row["recorded_by_user_id"]),
            kind=FineSettlementKind(str(row["kind"])),
            amount=_from_minor_units(int(row["amount_minor"])),
            note=str(note_value) if note_value is not None else None,
            created_at=from_database_datetime(str(row["created_at"])),
        )
