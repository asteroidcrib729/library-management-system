from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from psycopg import sql

from library_management.database import Database
from library_management.domain import User
from library_management.migration import SqlitePostgresImporter, create_sqlite_snapshot
from library_management.migration.errors import (
    LogicalRecoveryError,
    ReconciliationError,
    TargetNotEmptyError,
)
from library_management.postgres import PostgresDatabase
from library_management.postgres.recovery import (
    LogicalBackupArtifact,
    PostgresLogicalRecovery,
)
from library_management.repositories.postgres import PostgresUnitOfWork

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 9, 6, 8, 0, tzinfo=UTC).isoformat()


def seed_sqlite(path: Path) -> Path:
    database = Database(path)
    database.initialize()
    with database.connect() as connection:
        connection.executemany(
            """
            INSERT INTO users(id,display_name,username,password_hash,role,is_active,created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                (1, "Administrator", "admin.one", "$argon2id$admin", "administrator", 1, NOW),
                (2, "Member", "member.one", "$argon2id$member", "member", 1, NOW),
                (3, "Former", "former.one", "$argon2id$former", "member", 0, NOW),
            ),
        )
        connection.executemany(
            """
            INSERT INTO books(id,isbn,title,author,publication_year,category,description,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                (10, None, "Active Book", "Writer", 2025, "Fiction", "Active", NOW),
                (11, None, "Returned Book", "Writer", 2024, None, None, NOW),
            ),
        )
        connection.executemany(
            "INSERT INTO book_copies(id,book_id,barcode,status,created_at) VALUES (?,?,?,?,?)",
            ((20, 10, "COPY-020", "on_loan", NOW), (21, 11, "COPY-021", "available", NOW)),
        )
        connection.execute(
            """
            INSERT INTO reservations(id,user_id,book_id,status,created_at,resolved_at)
            VALUES (30,2,11,'fulfilled',?,?)
            """,
            (NOW, NOW),
        )
        connection.executemany(
            """
            INSERT INTO loans(
                id,user_id,book_copy_id,checked_out_at,due_at,returned_at,renewal_count)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                (40, 2, 20, NOW, "2026-09-20T08:00:00+00:00", None, 1),
                (41, 2, 21, NOW, "2026-09-10T08:00:00+00:00", NOW, 0),
            ),
        )
        connection.executemany(
            """
            INSERT INTO fines(
                id,user_id,loan_id,reason,amount_minor,status,assessed_at,settled_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                (50, 2, 40, "Outstanding", 1250, "outstanding", NOW, None),
                (51, 2, 41, "Paid", 500, "paid", NOW, NOW),
            ),
        )
        connection.execute(
            """
            INSERT INTO fine_settlements(
                id,fine_id,recorded_by_user_id,kind,amount_minor,note,created_at)
            VALUES (60,51,1,'payment',500,'Synthetic',?)
            """,
            (NOW,),
        )
        connection.executemany(
            """
            INSERT INTO book_requests(
                id,user_id,title,author,publication_year,status,created_at,
                reviewed_by_user_id,reviewed_at,review_note,acquired_book_id,
                acquired_by_user_id,acquired_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                (70, 2, "Acquired", "Author", 2026, "acquired", NOW, 1, NOW, None, 11, 1, NOW),
                (
                    71,
                    2,
                    "Pending",
                    "Author",
                    None,
                    "pending",
                    NOW,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            ),
        )
        connection.executemany(
            """
            INSERT INTO feedback(
                id,user_id,content,created_at,status,reviewed_by_user_id,reviewed_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            ((80, 2, "Reviewed", NOW, "reviewed", 1, NOW), (81, 2, "New", NOW, "new", None, None)),
        )
        connection.commit()
    return path


def test_dry_run_commit_reconciliation_sequences_and_source_immutability(
    migration_database: PostgresDatabase,
    tmp_path: Path,
) -> None:
    source = seed_sqlite(tmp_path / "source.db")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    snapshot = tmp_path / "migration.sqlite3"
    inspection = create_sqlite_snapshot(source, snapshot)
    importer = SqlitePostgresImporter(migration_database)

    dry_run = importer.run(snapshot)

    assert dry_run.dry_run
    assert dry_run.total_rows == 17
    assert dry_run.metrics == {
        "active_loans": 1,
        "active_reservations": 0,
        "outstanding_fines": 1,
        "outstanding_fine_minor": 1250,
        "settlement_minor": 500,
    }
    with migration_database.transaction() as transaction:
        assert transaction.connection.execute("SELECT count(*) AS n FROM users").fetchone() == {
            "n": 0
        }

    committed = importer.run(snapshot, dry_run=False)

    assert not committed.dry_run
    assert committed.row_counts == inspection.row_counts
    assert committed.row_digests == inspection.row_digests
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    with PostgresUnitOfWork(migration_database) as unit_of_work:
        added = unit_of_work.users.add(
            User(
                display_name="After Import",
                username="after.import",
                password_hash="$argon2id$after",
            )
        )
        unit_of_work.commit()
    assert added.id == 4
    with pytest.raises(TargetNotEmptyError, match="contains application data"):
        importer.run(snapshot, dry_run=False)


def test_reconciliation_failure_rolls_back_entire_import(
    migration_database: PostgresDatabase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = tmp_path / "migration.sqlite3"
    create_sqlite_snapshot(seed_sqlite(tmp_path / "source.db"), snapshot)
    importer = SqlitePostgresImporter(migration_database)

    def fail_reconciliation(*_: object) -> None:
        raise ReconciliationError("Synthetic reconciliation failure.")

    monkeypatch.setattr(importer, "_reconcile", fail_reconciliation)
    with pytest.raises(ReconciliationError, match="Synthetic"):
        importer.run(snapshot, dry_run=False)

    with migration_database.transaction() as transaction:
        for table in ("users", "books", "loans", "fines", "feedback"):
            row = transaction.connection.execute(
                sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier(table))
            ).fetchone()
            assert row == {"n": 0}


def test_logical_restore_refuses_existing_application_schema(
    migration_database: PostgresDatabase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "backup.dump"
    archive.write_bytes(b"synthetic archive")
    recovery = PostgresLogicalRecovery(migration_database.settings)

    def verified(_: Path) -> LogicalBackupArtifact:
        return LogicalBackupArtifact(archive, archive.stat().st_size, "a" * 64, 1)

    monkeypatch.setattr(recovery, "verify_backup", verified)

    with pytest.raises(LogicalRecoveryError, match="already contains"):
        recovery.restore_backup(archive)
