"""Ordered cross-database migration schema and canonical value rules."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

SQLITE_SCHEMA_VERSIONS = (1, 2, 3, 4)
POSTGRES_SCHEMA_VERSIONS = (1, 2, 3)

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": (
        "id",
        "display_name",
        "username",
        "password_hash",
        "role",
        "is_active",
        "created_at",
    ),
    "books": (
        "id",
        "isbn",
        "title",
        "author",
        "publication_year",
        "category",
        "description",
        "created_at",
    ),
    "book_copies": ("id", "book_id", "barcode", "status", "created_at"),
    "reservations": (
        "id",
        "user_id",
        "book_id",
        "status",
        "created_at",
        "resolved_at",
    ),
    "loans": (
        "id",
        "user_id",
        "book_copy_id",
        "checked_out_at",
        "due_at",
        "returned_at",
        "renewal_count",
    ),
    "fines": (
        "id",
        "user_id",
        "loan_id",
        "reason",
        "amount_minor",
        "status",
        "assessed_at",
        "settled_at",
    ),
    "fine_settlements": (
        "id",
        "fine_id",
        "recorded_by_user_id",
        "kind",
        "amount_minor",
        "note",
        "created_at",
    ),
    "book_requests": (
        "id",
        "user_id",
        "title",
        "author",
        "publication_year",
        "status",
        "created_at",
        "reviewed_by_user_id",
        "reviewed_at",
        "review_note",
        "acquired_book_id",
        "acquired_by_user_id",
        "acquired_at",
    ),
    "feedback": (
        "id",
        "user_id",
        "content",
        "created_at",
        "status",
        "reviewed_by_user_id",
        "reviewed_at",
    ),
}

DATETIME_COLUMNS = frozenset(
    {
        "created_at",
        "resolved_at",
        "checked_out_at",
        "due_at",
        "returned_at",
        "assessed_at",
        "settled_at",
        "reviewed_at",
        "acquired_at",
    }
)


def normalized_value(column: str, value: Any) -> str | int | bool | None:
    if value is None:
        return None
    if column == "is_active":
        return bool(value)
    if column in DATETIME_COLUMNS:
        timestamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError(f"Timestamp column {column} must include timezone information.")
        return timestamp.astimezone(UTC).isoformat(timespec="microseconds")
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    return str(value)


def canonical_rows(
    table: str,
    rows: Iterable[Mapping[str, Any]],
) -> list[list[str | int | bool | None]]:
    columns = TABLE_COLUMNS[table]
    return [[normalized_value(column, row[column]) for column in columns] for row in rows]


def canonical_digest(table: str, rows: Iterable[Mapping[str, Any]]) -> str:
    payload = json.dumps(
        canonical_rows(table, rows),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def rows_as_parameters(
    table: str,
    rows: Sequence[Any],
) -> list[tuple[Any, ...]]:
    parameters: list[tuple[Any, ...]] = []
    for row in rows:
        values: list[Any] = []
        for column in TABLE_COLUMNS[table]:
            value = row[column]
            if value is not None and column in DATETIME_COLUMNS:
                value = datetime.fromisoformat(str(value)).astimezone(UTC)
            elif column == "is_active":
                value = bool(value)
            values.append(value)
        parameters.append(tuple(values))
    return parameters
