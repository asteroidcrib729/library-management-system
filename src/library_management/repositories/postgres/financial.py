"""PostgreSQL fine and immutable-settlement repositories."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import psycopg
from psycopg import Connection

from library_management.domain import Fine, FineSettlement, FineSettlementKind, FineStatus
from library_management.postgres.database import Row
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.postgres.common import (
    as_datetime,
    optional_datetime,
    returned_row,
)

MINOR_UNITS = Decimal("100")


def _to_minor_units(amount: Decimal) -> int:
    return int(amount * MINOR_UNITS)


def _from_minor_units(amount: int) -> Decimal:
    return Decimal(amount) / MINOR_UNITS


class PostgresFineRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, fine: Fine) -> Fine:
        if fine.id is not None:
            raise ValueError("A new fine cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO fines(user_id, loan_id, reason, amount_minor, status,
                                      assessed_at, settled_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (
                        fine.user_id,
                        fine.loan_id,
                        fine.reason,
                        _to_minor_units(fine.amount),
                        fine.status.value,
                        fine.assessed_at,
                        fine.settled_at,
                    ),
                ),
                "fine identifier",
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError("The fine could not be created.") from error
        except psycopg.errors.ForeignKeyViolation as error:
            raise RecordNotFoundError("The fine user or loan was not found.") from error
        return replace(fine, id=int(row["id"]))

    def get_by_id(self, fine_id: int) -> Fine | None:
        row = self._connection.execute("SELECT * FROM fines WHERE id=%s", (fine_id,)).fetchone()
        return self._map(row) if row else None

    def get_by_loan_id(self, loan_id: int) -> Fine | None:
        row = self._connection.execute(
            "SELECT * FROM fines WHERE loan_id=%s ORDER BY id LIMIT 1", (loan_id,)
        ).fetchone()
        return self._map(row) if row else None

    def list_for_user(self, user_id: int) -> list[Fine]:
        rows = self._connection.execute(
            "SELECT * FROM fines WHERE user_id=%s ORDER BY assessed_at DESC, id DESC",
            (user_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    def settle(self, fine_id: int, status: FineStatus, settled_at: datetime) -> None:
        if status is FineStatus.OUTSTANDING:
            raise ValueError("Settlement status cannot be outstanding.")
        cursor = self._connection.execute(
            """
            UPDATE fines SET status=%s, settled_at=%s
            WHERE id=%s AND status='outstanding'
            """,
            (status.value, settled_at, fine_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Outstanding fine {fine_id} was not found.")

    @staticmethod
    def _map(row: Row) -> Fine:
        return Fine(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            loan_id=int(row["loan_id"]) if row["loan_id"] is not None else None,
            reason=str(row["reason"]),
            amount=_from_minor_units(int(row["amount_minor"])),
            status=FineStatus(str(row["status"])),
            assessed_at=as_datetime(row["assessed_at"]),
            settled_at=optional_datetime(row["settled_at"]),
        )


class PostgresFineSettlementRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, settlement: FineSettlement) -> FineSettlement:
        if settlement.id is not None:
            raise ValueError("A new settlement cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO fine_settlements(fine_id, recorded_by_user_id, kind,
                                                 amount_minor, note, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (
                        settlement.fine_id,
                        settlement.recorded_by_user_id,
                        settlement.kind.value,
                        _to_minor_units(settlement.amount),
                        settlement.note,
                        settlement.created_at,
                    ),
                ),
                "settlement identifier",
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError("This fine already has a settlement record.") from error
        except psycopg.errors.ForeignKeyViolation as error:
            raise RecordNotFoundError("The fine or recording user was not found.") from error
        return replace(settlement, id=int(row["id"]))

    def get_for_fine(self, fine_id: int) -> FineSettlement | None:
        row = self._connection.execute(
            "SELECT * FROM fine_settlements WHERE fine_id=%s", (fine_id,)
        ).fetchone()
        return self._map(row) if row else None

    def list_for_user(self, user_id: int) -> list[FineSettlement]:
        rows = self._connection.execute(
            """
            SELECT fine_settlements.* FROM fine_settlements
            JOIN fines ON fines.id=fine_settlements.fine_id
            WHERE fines.user_id=%s
            ORDER BY fine_settlements.created_at DESC, fine_settlements.id DESC
            """,
            (user_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: Row) -> FineSettlement:
        return FineSettlement(
            id=int(row["id"]),
            fine_id=int(row["fine_id"]),
            recorded_by_user_id=int(row["recorded_by_user_id"]),
            kind=FineSettlementKind(str(row["kind"])),
            amount=_from_minor_units(int(row["amount_minor"])),
            note=str(row["note"]) if row["note"] is not None else None,
            created_at=as_datetime(row["created_at"]),
        )
