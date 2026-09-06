"""SQLite user repository."""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from library_management.domain import User, UserRole
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.sqlite.mapping import (
    from_database_datetime,
    to_database_datetime,
)


class SqliteUserRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, user: User) -> User:
        if user.id is not None:
            raise ValueError("A new user cannot already have an identifier.")
        try:
            cursor = self._connection.execute(
                """
                INSERT INTO users(
                    display_name, username, password_hash, role, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.display_name,
                    user.username,
                    user.password_hash,
                    user.role.value,
                    int(user.is_active),
                    to_database_datetime(user.created_at),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError(f"Username '{user.username}' already exists.") from error
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the new user.")
        return replace(user, id=cursor.lastrowid)

    def get_by_id(self, user_id: int) -> User | None:
        row = self._connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._map(row) if row is not None else None

    def get_by_username(self, username: str) -> User | None:
        row = self._connection.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (username.strip().casefold(),),
        ).fetchone()
        return self._map(row) if row is not None else None

    def count_by_role(self, role: UserRole) -> int:
        row = self._connection.execute(
            "SELECT count(*) AS count FROM users WHERE role = ?",
            (role.value,),
        ).fetchone()
        return int(row["count"])

    def count_active_by_role(self, role: UserRole) -> int:
        row = self._connection.execute(
            "SELECT count(*) AS count FROM users WHERE role = ? AND is_active = 1",
            (role.value,),
        ).fetchone()
        return int(row["count"])

    def update_password_hash(self, user_id: int, password_hash: str) -> None:
        if not password_hash.strip():
            raise ValueError("Password hash must not be empty.")
        cursor = self._connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash.strip(), user_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"User {user_id} was not found.")

    def deactivate(self, user_id: int) -> None:
        cursor = self._connection.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"User {user_id} was not found.")

    @staticmethod
    def _map(row: sqlite3.Row) -> User:
        return User(
            id=int(row["id"]),
            display_name=str(row["display_name"]),
            username=str(row["username"]),
            password_hash=str(row["password_hash"]),
            role=UserRole(str(row["role"])),
            is_active=bool(row["is_active"]),
            created_at=from_database_datetime(str(row["created_at"])),
        )
