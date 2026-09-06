import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from library_management.database import MIGRATIONS, SCHEMA_VERSION, Database

EXPECTED_TABLES = {
    "book_copies",
    "book_requests",
    "books",
    "feedback",
    "fine_settlements",
    "fines",
    "loans",
    "reservations",
    "schema_migrations",
    "users",
}


def test_initialize_creates_versioned_schema(database: Database) -> None:
    with database.connect() as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        versions = [
            int(row["version"])
            for row in connection.execute("SELECT version FROM schema_migrations")
        ]

    assert tables == EXPECTED_TABLES
    assert versions == list(range(1, SCHEMA_VERSION + 1))


def test_initialize_is_idempotent(database: Database) -> None:
    database.initialize()
    database.initialize()

    with database.connect() as connection:
        migration_count = connection.execute(
            "SELECT count(*) AS count FROM schema_migrations"
        ).fetchone()["count"]

    assert migration_count == SCHEMA_VERSION


def test_connections_enforce_foreign_keys(database: Database) -> None:
    with database.connect() as connection:
        enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO book_copies(book_id, barcode, status, created_at)
                VALUES (999, 'MISSING-BOOK', 'available', '2026-01-01T00:00:00+00:00')
                """
            )

    assert enabled == 1


def test_version_one_database_migrates_existing_loan_without_data_loss(tmp_path: Path) -> None:
    database_path = tmp_path / "version-one.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) STRICT
        """
    )
    for statement in MIGRATIONS[1]:
        connection.execute(statement)
    connection.execute(
        "INSERT INTO schema_migrations(version, applied_at) VALUES (1, '2026-01-01T00:00:00+00:00')"
    )
    timestamp = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    connection.execute(
        """
        INSERT INTO users(display_name, username, password_hash, role, is_active, created_at)
        VALUES ('Reader', 'reader.one', 'hash', 'member', 1, ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO books(title, author, publication_year, created_at)
        VALUES ('Dune', 'Frank Herbert', 1965, ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO book_copies(book_id, barcode, status, created_at)
        VALUES (1, 'COPY-001', 'on_loan', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO loans(user_id, book_copy_id, checked_out_at, due_at)
        VALUES (1, 1, ?, '2026-01-15T00:00:00+00:00')
        """,
        (timestamp,),
    )
    connection.commit()
    connection.close()

    Database(database_path).initialize()

    with sqlite3.connect(database_path) as migrated:
        loan = migrated.execute(
            "SELECT user_id, book_copy_id, renewal_count FROM loans WHERE id = 1"
        ).fetchone()
        versions = [
            row[0]
            for row in migrated.execute("SELECT version FROM schema_migrations ORDER BY version")
        ]

    assert loan == (1, 1, 0)
    assert versions == [1, 2, 3, 4]


def test_version_two_database_migrates_existing_fine_without_data_loss(tmp_path: Path) -> None:
    database_path = tmp_path / "version-two.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) STRICT
        """
    )
    for version in (1, 2):
        for statement in MIGRATIONS[version]:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
    timestamp = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    connection.execute(
        """
        INSERT INTO users(display_name, username, password_hash, role, created_at)
        VALUES ('Reader', 'reader.one', 'hash', 'member', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO fines(user_id, reason, amount_minor, status, assessed_at)
        VALUES (1, 'Existing charge', 1050, 'outstanding', ?)
        """,
        (timestamp,),
    )
    connection.commit()
    connection.close()

    Database(database_path).initialize()

    with sqlite3.connect(database_path) as migrated:
        fine = migrated.execute(
            "SELECT user_id, reason, amount_minor, status FROM fines WHERE id = 1"
        ).fetchone()
        settlement_table = migrated.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'fine_settlements'"
        ).fetchone()

    assert fine == (1, "Existing charge", 1050, "outstanding")
    assert settlement_table == ("fine_settlements",)


def test_version_three_database_migrates_existing_submissions(tmp_path: Path) -> None:
    database_path = tmp_path / "version-three.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) STRICT
        """
    )
    for version in (1, 2, 3):
        for statement in MIGRATIONS[version]:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
    timestamp = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    connection.execute(
        """
        INSERT INTO users(display_name, username, password_hash, role, created_at)
        VALUES ('Reader', 'reader.one', 'hash', 'member', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO book_requests(user_id, title, author, publication_year, status, created_at)
        VALUES (1, 'Dune', 'Frank Herbert', 1965, 'pending', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        "INSERT INTO feedback(user_id, content, created_at) VALUES (1, 'More hours', ?)",
        (timestamp,),
    )
    connection.commit()
    connection.close()

    Database(database_path).initialize()

    with sqlite3.connect(database_path) as migrated:
        request = migrated.execute(
            """
            SELECT status, reviewed_by_user_id, acquired_book_id
            FROM book_requests WHERE id = 1
            """
        ).fetchone()
        feedback = migrated.execute(
            "SELECT content, status, reviewed_by_user_id FROM feedback WHERE id = 1"
        ).fetchone()

    assert request == ("pending", None, None)
    assert feedback == ("More hours", "new", None)
