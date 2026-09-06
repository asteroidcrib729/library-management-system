"""Shared conversion helpers for SQLite repositories."""

from datetime import datetime


def to_database_datetime(value: datetime) -> str:
    return value.isoformat()


def from_database_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
