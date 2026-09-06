"""PostgreSQL user repository."""

from __future__ import annotations

from dataclasses import replace

import psycopg
from psycopg import Connection

from library_management.domain import User, UserRole
from library_management.postgres.database import Row
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.postgres.common import as_datetime, returned_row


class PostgresUserRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, user: User) -> User:
        if user.id is not None:
            raise ValueError("A new user cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO users(display_name, username, password_hash, role, is_active,
                                      created_at)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (
                        user.display_name,
                        user.username,
                        user.password_hash,
                        user.role.value,
                        user.is_active,
                        user.created_at,
                    ),
                ),
                "user identifier",
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError(f"Username '{user.username}' already exists.") from error
        return replace(user, id=int(row["id"]))

    def get_by_id(self, user_id: int) -> User | None:
        row = self._connection.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
        return self._map(row) if row else None

    def get_by_username(self, username: str) -> User | None:
        row = self._connection.execute(
            "SELECT * FROM users WHERE lower(username) = lower(%s)",
            (username.strip(),),
        ).fetchone()
        return self._map(row) if row else None

    def count_by_role(self, role: UserRole) -> int:
        row = returned_row(
            self._connection.execute(
                "SELECT count(*) AS count FROM users WHERE role = %s", (role.value,)
            ),
            "role count",
        )
        return int(row["count"])

    def count_active_by_role(self, role: UserRole) -> int:
        row = returned_row(
            self._connection.execute(
                "SELECT count(*) AS count FROM users WHERE role = %s AND is_active",
                (role.value,),
            ),
            "active role count",
        )
        return int(row["count"])

    def update_password_hash(self, user_id: int, password_hash: str) -> None:
        if not password_hash.strip():
            raise ValueError("Password hash must not be empty.")
        cursor = self._connection.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash.strip(), user_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"User {user_id} was not found.")

    def deactivate(self, user_id: int) -> None:
        cursor = self._connection.execute(
            "UPDATE users SET is_active = false WHERE id = %s AND is_active",
            (user_id,),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Active user {user_id} was not found.")

    @staticmethod
    def _map(row: Row) -> User:
        return User(
            id=int(row["id"]),
            display_name=str(row["display_name"]),
            username=str(row["username"]),
            password_hash=str(row["password_hash"]),
            role=UserRole(str(row["role"])),
            is_active=bool(row["is_active"]),
            created_at=as_datetime(row["created_at"]),
        )
