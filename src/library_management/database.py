"""SQLite connection configuration and versioned schema management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 4

MIGRATIONS: dict[int, tuple[str, ...]] = {
    1: (
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            display_name TEXT NOT NULL CHECK (length(trim(display_name)) > 0),
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL CHECK (length(password_hash) > 0),
            role TEXT NOT NULL CHECK (role IN ('member', 'librarian', 'administrator')),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL
        ) STRICT
        """,
        """
        CREATE TABLE books (
            id INTEGER PRIMARY KEY,
            isbn TEXT COLLATE NOCASE UNIQUE,
            title TEXT NOT NULL CHECK (length(trim(title)) > 0),
            author TEXT NOT NULL CHECK (length(trim(author)) > 0),
            publication_year INTEGER NOT NULL CHECK (publication_year BETWEEN 1 AND 9999),
            category TEXT,
            description TEXT,
            created_at TEXT NOT NULL
        ) STRICT
        """,
        """
        CREATE UNIQUE INDEX books_identity_uq
        ON books(lower(title), lower(author), publication_year)
        """,
        "CREATE INDEX books_title_idx ON books(title COLLATE NOCASE)",
        "CREATE INDEX books_author_idx ON books(author COLLATE NOCASE)",
        """
        CREATE TABLE book_copies (
            id INTEGER PRIMARY KEY,
            book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
            barcode TEXT NOT NULL COLLATE NOCASE UNIQUE,
            status TEXT NOT NULL CHECK (
                status IN ('available', 'on_loan', 'lost', 'damaged', 'withdrawn')
            ),
            created_at TEXT NOT NULL
        ) STRICT
        """,
        "CREATE INDEX book_copies_book_status_idx ON book_copies(book_id, status)",
        """
        CREATE TABLE reservations (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
            status TEXT NOT NULL CHECK (
                status IN ('active', 'fulfilled', 'cancelled', 'expired')
            ),
            created_at TEXT NOT NULL,
            resolved_at TEXT
        ) STRICT
        """,
        """
        CREATE UNIQUE INDEX reservations_active_user_book_uq
        ON reservations(user_id, book_id) WHERE status = 'active'
        """,
        """
        CREATE INDEX reservations_queue_idx
        ON reservations(book_id, status, created_at, id)
        """,
        """
        CREATE TABLE loans (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            book_copy_id INTEGER NOT NULL REFERENCES book_copies(id) ON DELETE RESTRICT,
            checked_out_at TEXT NOT NULL,
            due_at TEXT NOT NULL,
            returned_at TEXT,
            CHECK (due_at > checked_out_at),
            CHECK (returned_at IS NULL OR returned_at >= checked_out_at)
        ) STRICT
        """,
        """
        CREATE UNIQUE INDEX loans_active_copy_uq
        ON loans(book_copy_id) WHERE returned_at IS NULL
        """,
        "CREATE INDEX loans_user_idx ON loans(user_id, returned_at, due_at)",
        """
        CREATE TABLE fines (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            loan_id INTEGER REFERENCES loans(id) ON DELETE RESTRICT,
            reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
            amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
            status TEXT NOT NULL CHECK (status IN ('outstanding', 'paid', 'waived')),
            assessed_at TEXT NOT NULL,
            settled_at TEXT
        ) STRICT
        """,
        "CREATE INDEX fines_user_status_idx ON fines(user_id, status)",
        """
        CREATE TABLE book_requests (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title TEXT NOT NULL CHECK (length(trim(title)) > 0),
            author TEXT NOT NULL CHECK (length(trim(author)) > 0),
            publication_year INTEGER CHECK (publication_year BETWEEN 1 AND 9999),
            status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'acquired')),
            created_at TEXT NOT NULL
        ) STRICT
        """,
        "CREATE INDEX book_requests_user_status_idx ON book_requests(user_id, status)",
        """
        CREATE TABLE feedback (
            id INTEGER PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            content TEXT NOT NULL CHECK (length(trim(content)) > 0),
            created_at TEXT NOT NULL
        ) STRICT
        """,
    ),
    2: (
        """
        ALTER TABLE loans
        ADD COLUMN renewal_count INTEGER NOT NULL DEFAULT 0
        CHECK (renewal_count >= 0)
        """,
    ),
    3: (
        """
        CREATE TABLE fine_settlements (
            id INTEGER PRIMARY KEY,
            fine_id INTEGER NOT NULL UNIQUE REFERENCES fines(id) ON DELETE RESTRICT,
            recorded_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            kind TEXT NOT NULL CHECK (kind IN ('payment', 'waiver')),
            amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
            note TEXT,
            created_at TEXT NOT NULL
        ) STRICT
        """,
        "CREATE INDEX fine_settlements_actor_idx ON fine_settlements(recorded_by_user_id)",
    ),
    4: (
        """
        ALTER TABLE book_requests ADD COLUMN reviewed_by_user_id INTEGER
        REFERENCES users(id) ON DELETE RESTRICT
        """,
        "ALTER TABLE book_requests ADD COLUMN reviewed_at TEXT",
        "ALTER TABLE book_requests ADD COLUMN review_note TEXT",
        """
        ALTER TABLE book_requests ADD COLUMN acquired_book_id INTEGER
        REFERENCES books(id) ON DELETE RESTRICT
        """,
        """
        ALTER TABLE book_requests ADD COLUMN acquired_by_user_id INTEGER
        REFERENCES users(id) ON DELETE RESTRICT
        """,
        "ALTER TABLE book_requests ADD COLUMN acquired_at TEXT",
        "CREATE INDEX book_requests_status_idx ON book_requests(status, created_at, id)",
        """
        ALTER TABLE feedback ADD COLUMN status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'reviewed', 'archived'))
        """,
        """
        ALTER TABLE feedback ADD COLUMN reviewed_by_user_id INTEGER
        REFERENCES users(id) ON DELETE RESTRICT
        """,
        "ALTER TABLE feedback ADD COLUMN reviewed_at TEXT",
        "CREATE INDEX feedback_status_idx ON feedback(status, created_at, id)",
    ),
}


class UnsupportedSchemaVersionError(RuntimeError):
    """Raised when a database is newer than this application supports."""


class Database:
    """Create configured SQLite connections and apply schema migrations."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize(self) -> None:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) STRICT
                """
            )
            applied_versions = {
                int(row["version"])
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            if any(version > SCHEMA_VERSION for version in applied_versions):
                raise UnsupportedSchemaVersionError(
                    "Database schema is newer than this application supports."
                )

            for version in range(1, SCHEMA_VERSION + 1):
                if version in applied_versions:
                    continue
                for statement in MIGRATIONS[version]:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)",
                    (version,),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
