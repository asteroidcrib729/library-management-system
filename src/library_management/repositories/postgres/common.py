"""Mapping and database-error helpers shared by PostgreSQL repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg

from library_management.postgres.database import Row


def as_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise RuntimeError("PostgreSQL returned an invalid timestamp value.")
    return value


def optional_datetime(value: Any) -> datetime | None:
    return None if value is None else as_datetime(value)


def returned_row(cursor: psycopg.Cursor[Row], entity: str) -> Row:
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"PostgreSQL did not return the new {entity}.")
    return row
