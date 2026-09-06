import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

import pytest

from library_management.database import SCHEMA_VERSION, Database
from library_management.domain import Book, BookCopy, BookCopyStatus, User, UserRole
from library_management.repositories import UnitOfWork
from library_management.repositories.sqlite import SqliteUnitOfWork
from library_management.services import (
    AuthorizationError,
    BackupNotFoundError,
    BackupValidationError,
    MaintenanceService,
)

NOW = datetime(2026, 5, 1, 8, 30, tzinfo=UTC)


def build_factory(database: Database) -> Callable[[], UnitOfWork]:
    return partial(SqliteUnitOfWork, database)


def build_service(database: Database, backup_directory: Path) -> MaintenanceService:
    return MaintenanceService(
        build_factory(database),
        database,
        backup_directory,
        clock=lambda: NOW,
    )


def add_user(database: Database, username: str, role: UserRole = UserRole.MEMBER) -> User:
    with SqliteUnitOfWork(database) as unit_of_work:
        user = unit_of_work.users.add(
            User(
                display_name=username,
                username=username,
                password_hash="$argon2id$test-hash",
                role=role,
            )
        )
        unit_of_work.commit()
    return user


def test_initialized_database_passes_health_checks(database: Database, tmp_path: Path) -> None:
    administrator = add_user(database, "admin.one", UserRole.ADMINISTRATOR)
    service = build_service(database, tmp_path / "backups")

    health = service.health(administrator.id or 0)

    assert health.is_healthy
    assert health.is_compatible
    assert health.applied_versions == tuple(range(1, SCHEMA_VERSION + 1))
    assert health.integrity_messages == ("ok",)
    assert health.foreign_key_violations == 0


def test_health_reports_logical_inconsistencies(database: Database, tmp_path: Path) -> None:
    administrator = add_user(database, "admin.one", UserRole.ADMINISTRATOR)
    member = add_user(database, "reader.one")
    with SqliteUnitOfWork(database) as unit_of_work:
        book = unit_of_work.books.add(
            Book(title="Dune", author="Frank Herbert", publication_year=1965)
        )
        unit_of_work.book_copies.add(
            BookCopy(
                book_id=book.id or 0,
                barcode="COPY-001",
                status=BookCopyStatus.ON_LOAN,
            )
        )
        unit_of_work.commit()
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO fines(
                user_id, reason, amount_minor, status, assessed_at, settled_at
            ) VALUES (?, 'Broken settlement', 1000, 'paid', ?, ?)
            """,
            (member.id, NOW.isoformat(), NOW.isoformat()),
        )
        connection.commit()
    service = build_service(database, tmp_path / "backups")

    health = service.health(administrator.id or 0)

    assert not health.is_healthy
    assert health.circulation_inconsistencies == 1
    assert health.financial_inconsistencies == 1


def test_backup_is_valid_snapshot_and_names_do_not_collide(
    database: Database, tmp_path: Path
) -> None:
    administrator = add_user(database, "admin.one", UserRole.ADMINISTRATOR)
    add_user(database, "reader.one")
    service = build_service(database, tmp_path / "backups")

    first = service.create_backup(administrator.id or 0)
    add_user(database, "reader.two")
    second = service.create_backup(administrator.id or 0)

    assert first.filename != second.filename
    assert first.health.is_healthy
    with sqlite3.connect(tmp_path / "backups" / first.filename) as snapshot:
        saved_user_count = snapshot.execute("SELECT count(*) FROM users").fetchone()[0]
    assert saved_user_count == 2
    assert [item.filename for item in service.list_backups(administrator.id or 0)] == [
        second.filename,
        first.filename,
    ]


def test_restore_recovers_snapshot_and_creates_safety_backup(
    database: Database, tmp_path: Path
) -> None:
    administrator = add_user(database, "admin.one", UserRole.ADMINISTRATOR)
    add_user(database, "reader.one")
    service = build_service(database, tmp_path / "backups")
    snapshot = service.create_backup(administrator.id or 0)
    add_user(database, "reader.two")

    result = service.restore_backup(administrator.id or 0, snapshot.filename)

    assert result.health.is_healthy
    assert result.restored_backup.filename == snapshot.filename
    assert result.safety_backup.filename.startswith("pre-restore-")
    with sqlite3.connect(tmp_path / "backups" / result.safety_backup.filename) as safety:
        safety_usernames = {
            row[0] for row in safety.execute("SELECT username FROM users ORDER BY username")
        }
    assert "reader.two" in safety_usernames
    with SqliteUnitOfWork(database) as unit_of_work:
        restored_first = unit_of_work.users.get_by_username("reader.one")
        restored_second = unit_of_work.users.get_by_username("reader.two")
    assert restored_first is not None
    assert restored_second is None


def test_corrupt_backup_is_listed_but_cannot_replace_live_database(
    database: Database, tmp_path: Path
) -> None:
    administrator = add_user(database, "admin.one", UserRole.ADMINISTRATOR)
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()
    corrupt = backup_directory / "corrupt.sqlite3"
    corrupt.write_bytes(b"not a sqlite database")
    service = build_service(database, backup_directory)

    listed = service.list_backups(administrator.id or 0)

    assert listed[0].filename == corrupt.name
    assert not listed[0].health.is_healthy
    with pytest.raises(BackupValidationError, match="failed"):
        service.restore_backup(administrator.id or 0, corrupt.name)
    with SqliteUnitOfWork(database) as unit_of_work:
        assert unit_of_work.users.get_by_username("admin.one") is not None


def test_schema_incompatible_backup_cannot_be_restored(database: Database, tmp_path: Path) -> None:
    administrator = add_user(database, "admin.one", UserRole.ADMINISTRATOR)
    backup_directory = tmp_path / "backups"
    service = build_service(database, backup_directory)
    backup = service.create_backup(administrator.id or 0)
    with sqlite3.connect(backup_directory / backup.filename) as incompatible:
        incompatible.execute("INSERT INTO schema_migrations(version) VALUES (999)")
        incompatible.commit()

    listed = service.list_backups(administrator.id or 0)

    assert not listed[0].health.is_compatible
    with pytest.raises(BackupValidationError, match="failed"):
        service.restore_backup(administrator.id or 0, backup.filename)
    assert service.health(administrator.id or 0).is_healthy


def test_restore_rejects_traversal_and_missing_backup(database: Database, tmp_path: Path) -> None:
    administrator = add_user(database, "admin.one", UserRole.ADMINISTRATOR)
    service = build_service(database, tmp_path / "backups")

    with pytest.raises(BackupNotFoundError, match="managed"):
        service.restore_backup(administrator.id or 0, "../outside.sqlite3")
    with pytest.raises(BackupNotFoundError, match="not found"):
        service.restore_backup(administrator.id or 0, "missing.sqlite3")


def test_maintenance_operations_require_administrator(database: Database, tmp_path: Path) -> None:
    member = add_user(database, "reader.one")
    service = build_service(database, tmp_path / "backups")

    with pytest.raises(AuthorizationError, match="Administrator"):
        service.health(member.id or 0)
    with pytest.raises(AuthorizationError, match="Administrator"):
        service.create_backup(member.id or 0)
    with pytest.raises(AuthorizationError, match="Administrator"):
        service.list_backups(member.id or 0)
    with pytest.raises(AuthorizationError, match="Administrator"):
        service.restore_backup(member.id or 0, "missing.sqlite3")
