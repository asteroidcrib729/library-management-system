"""Create and validate immutable SQLite migration snapshots."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from library_management.migration.errors import SnapshotValidationError
from library_management.migration.schema import (
    SQLITE_SCHEMA_VERSIONS,
    TABLE_COLUMNS,
    canonical_digest,
)


@dataclass(frozen=True, slots=True)
class SnapshotInspection:
    path: Path
    size_bytes: int
    file_sha256: str
    schema_versions: tuple[int, ...]
    row_counts: dict[str, int]
    row_digests: dict[str, str]
    metrics: dict[str, int]


def create_sqlite_snapshot(source: Path, destination: Path) -> SnapshotInspection:
    source = source.resolve()
    destination = destination.resolve()
    if source == destination:
        raise SnapshotValidationError("Snapshot destination must differ from its source.")
    if not source.is_file():
        raise SnapshotValidationError("SQLite source file does not exist.")
    if destination.exists():
        raise SnapshotValidationError("Snapshot destination already exists.")
    destination.parent.mkdir(parents=True, exist_ok=True)

    before = source.stat()
    source_connection = _connect_read_only(source, immutable=False)
    destination_connection = sqlite3.connect(destination)
    try:
        data_version = int(source_connection.execute("PRAGMA data_version").fetchone()[0])
        source_connection.backup(destination_connection)
        destination_connection.commit()
        if int(source_connection.execute("PRAGMA data_version").fetchone()[0]) != data_version:
            raise SnapshotValidationError("SQLite source changed while its snapshot was created.")
    except Exception:
        destination_connection.close()
        source_connection.close()
        destination.unlink(missing_ok=True)
        raise
    else:
        destination_connection.close()
        source_connection.close()

    after = source.stat()
    if (
        (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        destination.unlink(missing_ok=True)
        raise SnapshotValidationError("SQLite source was replaced while its snapshot was created.")
    try:
        return inspect_sqlite_snapshot(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def inspect_sqlite_snapshot(path: Path) -> SnapshotInspection:
    path = path.resolve()
    if not path.is_file():
        raise SnapshotValidationError("SQLite snapshot file does not exist.")
    if Path(f"{path}-wal").exists() or Path(f"{path}-shm").exists():
        raise SnapshotValidationError("SQLite snapshot must be a closed standalone file.")
    try:
        connection = _connect_read_only(path, immutable=True)
        connection.row_factory = sqlite3.Row
        try:
            integrity = tuple(str(row[0]) for row in connection.execute("PRAGMA integrity_check"))
            if integrity != ("ok",):
                raise SnapshotValidationError("SQLite snapshot failed its integrity check.")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise SnapshotValidationError("SQLite snapshot contains foreign-key violations.")
            versions = tuple(
                int(row[0])
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            )
            if versions != SQLITE_SCHEMA_VERSIONS:
                raise SnapshotValidationError(
                    "SQLite snapshot schema is incomplete or unsupported."
                )
            _validate_tables(connection)
            _validate_identifiers(connection)
            _validate_state(connection)
            counts, digests = _summaries(connection)
            metrics = _metrics(connection)
        finally:
            connection.close()
    except SnapshotValidationError:
        raise
    except (OSError, sqlite3.DatabaseError, ValueError, TypeError) as error:
        raise SnapshotValidationError("SQLite snapshot could not be validated safely.") from error
    return SnapshotInspection(
        path=path,
        size_bytes=path.stat().st_size,
        file_sha256=_file_digest(path),
        schema_versions=versions,
        row_counts=counts,
        row_digests=digests,
        metrics=metrics,
    )


def _connect_read_only(path: Path, *, immutable: bool) -> sqlite3.Connection:
    suffix = "?mode=ro&immutable=1" if immutable else "?mode=ro"
    return sqlite3.connect(f"{path.as_uri()}{suffix}", uri=True)


def _validate_tables(connection: sqlite3.Connection) -> None:
    stored = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    required = set(TABLE_COLUMNS) | {"schema_migrations"}
    if not required <= stored:
        raise SnapshotValidationError("SQLite snapshot is missing required application tables.")
    for table, columns in TABLE_COLUMNS.items():
        available = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
        if not set(columns) <= available:
            raise SnapshotValidationError(f"SQLite snapshot table {table} is incompatible.")


def _validate_identifiers(connection: sqlite3.Connection) -> None:
    for table in TABLE_COLUMNS:
        if connection.execute(f"SELECT 1 FROM {table} WHERE id <= 0 LIMIT 1").fetchone():
            raise SnapshotValidationError("SQLite snapshot contains a non-positive identifier.")


def _validate_state(connection: sqlite3.Connection) -> None:
    statements = (
        """
        SELECT 1 FROM reservations
        WHERE (status='active') <> (resolved_at IS NULL) LIMIT 1
        """,
        """
        SELECT 1 FROM book_copies
        LEFT JOIN loans ON loans.book_copy_id=book_copies.id AND loans.returned_at IS NULL
        WHERE (book_copies.status='on_loan') <> (loans.id IS NOT NULL) LIMIT 1
        """,
        """
        SELECT 1 FROM fines
        LEFT JOIN fine_settlements ON fine_settlements.fine_id=fines.id
        WHERE (fines.status='outstanding') <> (fines.settled_at IS NULL)
           OR (fines.status='outstanding') <> (fine_settlements.id IS NULL)
           OR (fines.status='paid' AND fine_settlements.kind <> 'payment')
           OR (fines.status='waived' AND fine_settlements.kind <> 'waiver')
           OR (fine_settlements.id IS NOT NULL
               AND fine_settlements.amount_minor <> fines.amount_minor)
        LIMIT 1
        """,
        """
        SELECT 1 FROM book_requests
        WHERE (status='pending') <> (reviewed_at IS NULL)
           OR (reviewed_at IS NULL) <> (reviewed_by_user_id IS NULL)
           OR (status='acquired') <> (acquired_at IS NOT NULL)
           OR (acquired_at IS NULL) <> (acquired_book_id IS NULL)
           OR (acquired_at IS NULL) <> (acquired_by_user_id IS NULL)
           OR (status='rejected' AND length(trim(coalesce(review_note, '')))=0)
        LIMIT 1
        """,
        """
        SELECT 1 FROM feedback
        WHERE (status='new') <> (reviewed_at IS NULL)
           OR (reviewed_at IS NULL) <> (reviewed_by_user_id IS NULL)
        LIMIT 1
        """,
    )
    if any(connection.execute(statement).fetchone() is not None for statement in statements):
        raise SnapshotValidationError("SQLite snapshot contains invalid application state.")


def _summaries(connection: sqlite3.Connection) -> tuple[dict[str, int], dict[str, str]]:
    counts: dict[str, int] = {}
    digests: dict[str, str] = {}
    for table, columns in TABLE_COLUMNS.items():
        column_list = ", ".join(columns)
        rows = connection.execute(f"SELECT {column_list} FROM {table} ORDER BY id").fetchall()
        counts[table] = len(rows)
        digests[table] = canonical_digest(table, rows)
    return counts, digests


def _metrics(connection: sqlite3.Connection) -> dict[str, int]:
    statements = {
        "active_loans": "SELECT count(*) FROM loans WHERE returned_at IS NULL",
        "active_reservations": "SELECT count(*) FROM reservations WHERE status='active'",
        "outstanding_fines": "SELECT count(*) FROM fines WHERE status='outstanding'",
        "outstanding_fine_minor": (
            "SELECT coalesce(sum(amount_minor),0) FROM fines WHERE status='outstanding'"
        ),
        "settlement_minor": "SELECT coalesce(sum(amount_minor),0) FROM fine_settlements",
    }
    return {
        name: int(connection.execute(statement).fetchone()[0])
        for name, statement in statements.items()
    }


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
