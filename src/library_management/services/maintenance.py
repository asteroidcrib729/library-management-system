"""Administrator-only SQLite health, backup, and restoration operations."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from library_management.database import SCHEMA_VERSION, Database
from library_management.domain import UserRole
from library_management.services.accounts import UnitOfWorkFactory
from library_management.services.authorization import require_role
from library_management.services.errors import BackupNotFoundError, BackupValidationError

Clock = Callable[[], datetime]
ADMINISTRATOR_ROLE = frozenset({UserRole.ADMINISTRATOR})


def system_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    checked_at: datetime
    path: Path
    file_size_bytes: int
    applied_versions: tuple[int, ...]
    expected_version: int
    integrity_messages: tuple[str, ...]
    foreign_key_violations: int
    circulation_inconsistencies: int
    financial_inconsistencies: int
    inspection_error: str | None = None

    @property
    def schema_version(self) -> int | None:
        return self.applied_versions[-1] if self.applied_versions else None

    @property
    def is_compatible(self) -> bool:
        return self.applied_versions == tuple(range(1, self.expected_version + 1))

    @property
    def is_healthy(self) -> bool:
        return (
            self.inspection_error is None
            and self.integrity_messages == ("ok",)
            and self.foreign_key_violations == 0
            and self.is_compatible
            and self.circulation_inconsistencies == 0
            and self.financial_inconsistencies == 0
        )


@dataclass(frozen=True, slots=True)
class BackupInfo:
    filename: str
    created_at: datetime
    size_bytes: int
    health: DatabaseHealth


@dataclass(frozen=True, slots=True)
class RestoreResult:
    restored_backup: BackupInfo
    safety_backup: BackupInfo
    health: DatabaseHealth


class MaintenanceService:
    """Perform guarded maintenance without exposing arbitrary filesystem paths."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        database: Database,
        backup_directory: Path,
        clock: Clock = system_clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._database = database
        self._backup_directory = backup_directory
        self._clock = clock

    def health(self, actor_id: int) -> DatabaseHealth:
        self._authorize(actor_id)
        return self._inspect(self._database.path)

    def create_backup(self, actor_id: int) -> BackupInfo:
        self._authorize(actor_id)
        return self._create_backup("library")

    def list_backups(self, actor_id: int) -> list[BackupInfo]:
        self._authorize(actor_id)
        self._backup_directory.mkdir(parents=True, exist_ok=True)
        backups = [
            self._backup_info(path)
            for path in self._backup_directory.glob("*.sqlite3")
            if path.is_file()
        ]
        backups.sort(key=self._backup_sort_key, reverse=True)
        return backups

    def restore_backup(self, actor_id: int, filename: str) -> RestoreResult:
        self._authorize(actor_id)
        source = self._managed_backup_path(filename)
        if not source.is_file():
            raise BackupNotFoundError(f"Backup '{filename}' was not found.")
        restored_info = self._backup_info(source)
        if not restored_info.health.is_healthy:
            raise BackupValidationError(
                "The selected backup failed integrity, schema, or consistency validation."
            )

        safety_backup = self._create_backup("pre-restore")
        temporary = self._database.path.with_name(
            f".{self._database.path.name}.restore-{uuid4().hex}.tmp"
        )
        try:
            self._copy_database(source, temporary)
            staged_health = self._inspect(temporary)
            if not staged_health.is_healthy:
                raise BackupValidationError("The staged restore database failed validation.")
            os.replace(temporary, self._database.path)
            try:
                self._database.initialize()
                final_health = self._inspect(self._database.path)
                if not final_health.is_healthy:
                    raise BackupValidationError(
                        "The restored database failed final health validation."
                    )
            except Exception as error:
                self._restore_safety_copy(safety_backup)
                if isinstance(error, BackupValidationError):
                    raise
                raise BackupValidationError(
                    "Restoration failed; the pre-restore safety backup was recovered."
                ) from error
        finally:
            temporary.unlink(missing_ok=True)

        return RestoreResult(restored_info, safety_backup, final_health)

    def _create_backup(self, prefix: str) -> BackupInfo:
        current_health = self._inspect(self._database.path)
        if not current_health.is_healthy:
            raise BackupValidationError(
                "The active database failed health validation and was not backed up."
            )
        self._backup_directory.mkdir(parents=True, exist_ok=True)
        destination = self._available_backup_path(prefix)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            self._copy_database(self._database.path, temporary)
            backup_health = self._inspect(temporary)
            if not backup_health.is_healthy:
                raise BackupValidationError("The new backup failed validation.")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return self._backup_info(destination)

    def _restore_safety_copy(self, safety_backup: BackupInfo) -> None:
        source = self._managed_backup_path(safety_backup.filename)
        temporary = self._database.path.with_name(
            f".{self._database.path.name}.recovery-{uuid4().hex}.tmp"
        )
        try:
            self._copy_database(source, temporary)
            os.replace(temporary, self._database.path)
            self._database.initialize()
        finally:
            temporary.unlink(missing_ok=True)

    def _available_backup_path(self, prefix: str) -> Path:
        timestamp = self._now().strftime("%Y%m%dT%H%M%S%fZ")
        base = self._backup_directory / f"{prefix}-{timestamp}.sqlite3"
        if not base.exists():
            return base
        for suffix in range(1, 1000):
            candidate = self._backup_directory / f"{prefix}-{timestamp}-{suffix:03d}.sqlite3"
            if not candidate.exists():
                return candidate
        raise BackupValidationError("A collision-free backup filename could not be generated.")

    def _managed_backup_path(self, filename: str) -> Path:
        cleaned = filename.strip()
        if not cleaned or Path(cleaned).name != cleaned:
            raise BackupNotFoundError("A managed backup filename is required.")
        candidate = (self._backup_directory / cleaned).resolve()
        if candidate.parent != self._backup_directory.resolve():
            raise BackupNotFoundError("A managed backup filename is required.")
        return candidate

    def _backup_info(self, path: Path) -> BackupInfo:
        stat = path.stat()
        return BackupInfo(
            filename=path.name,
            created_at=datetime.fromtimestamp(stat.st_mtime, UTC),
            size_bytes=stat.st_size,
            health=self._inspect(path),
        )

    @staticmethod
    def _backup_sort_key(item: BackupInfo) -> tuple[datetime, str]:
        return item.created_at, item.filename

    @staticmethod
    def _copy_database(source: Path, destination: Path) -> None:
        source_connection = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
        destination_connection = sqlite3.connect(destination)
        try:
            source_connection.backup(destination_connection)
            destination_connection.commit()
        finally:
            destination_connection.close()
            source_connection.close()

    def _inspect(self, path: Path) -> DatabaseHealth:
        checked_at = self._now()
        if not path.is_file():
            return self._failed_health(path, checked_at, "Database file does not exist.")
        try:
            connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            try:
                integrity_messages = tuple(
                    str(row[0]) for row in connection.execute("PRAGMA integrity_check")
                )
                foreign_key_violations = len(
                    connection.execute("PRAGMA foreign_key_check").fetchall()
                )
                applied_versions = tuple(
                    int(row[0])
                    for row in connection.execute(
                        "SELECT version FROM schema_migrations ORDER BY version"
                    )
                )
                circulation_inconsistencies = self._circulation_inconsistencies(connection)
                financial_inconsistencies = self._financial_inconsistencies(connection)
            finally:
                connection.close()
        except (OSError, sqlite3.DatabaseError) as error:
            return self._failed_health(path, checked_at, str(error))
        return DatabaseHealth(
            checked_at=checked_at,
            path=path,
            file_size_bytes=path.stat().st_size,
            applied_versions=applied_versions,
            expected_version=SCHEMA_VERSION,
            integrity_messages=integrity_messages,
            foreign_key_violations=foreign_key_violations,
            circulation_inconsistencies=circulation_inconsistencies,
            financial_inconsistencies=financial_inconsistencies,
        )

    @staticmethod
    def _circulation_inconsistencies(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            """
            SELECT count(*) FROM book_copies
            LEFT JOIN loans
              ON loans.book_copy_id = book_copies.id AND loans.returned_at IS NULL
            WHERE (book_copies.status = 'on_loan' AND loans.id IS NULL)
               OR (book_copies.status <> 'on_loan' AND loans.id IS NOT NULL)
            """
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _financial_inconsistencies(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            """
            SELECT count(*) FROM fines
            LEFT JOIN fine_settlements ON fine_settlements.fine_id = fines.id
            WHERE (fines.status = 'outstanding' AND (
                       fines.settled_at IS NOT NULL OR fine_settlements.id IS NOT NULL
                   ))
               OR (fines.status <> 'outstanding' AND (
                       fines.settled_at IS NULL OR fine_settlements.id IS NULL
                   ))
               OR (fines.status = 'paid' AND fine_settlements.kind <> 'payment')
               OR (fines.status = 'waived' AND fine_settlements.kind <> 'waiver')
               OR (fine_settlements.id IS NOT NULL
                   AND fine_settlements.amount_minor <> fines.amount_minor)
            """
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _failed_health(path: Path, checked_at: datetime, message: str) -> DatabaseHealth:
        size = path.stat().st_size if path.is_file() else 0
        return DatabaseHealth(
            checked_at=checked_at,
            path=path,
            file_size_bytes=size,
            applied_versions=(),
            expected_version=SCHEMA_VERSION,
            integrity_messages=(),
            foreign_key_violations=0,
            circulation_inconsistencies=0,
            financial_inconsistencies=0,
            inspection_error=message,
        )

    def _authorize(self, actor_id: int) -> None:
        with self._unit_of_work_factory() as unit_of_work:
            require_role(
                unit_of_work,
                actor_id,
                ADMINISTRATOR_ROLE,
                "Administrator permission is required.",
            )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Maintenance clock must return a timezone-aware timestamp.")
        return value.astimezone(UTC)
