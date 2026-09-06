import hashlib
import sqlite3
from pathlib import Path

import pytest

from library_management.database import Database
from library_management.migration.errors import SnapshotValidationError
from library_management.migration.snapshot import (
    create_sqlite_snapshot,
    inspect_sqlite_snapshot,
)


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_snapshot_creation_is_read_only_and_requires_new_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    Database(source).initialize()
    before = file_digest(source)
    snapshot = tmp_path / "snapshots" / "migration.sqlite3"

    inspection = create_sqlite_snapshot(source, snapshot)

    assert file_digest(source) == before
    assert inspection.schema_versions == (1, 2, 3, 4)
    assert inspection.row_counts == {name: 0 for name in inspection.row_counts}
    assert inspect_sqlite_snapshot(snapshot) == inspection
    with pytest.raises(SnapshotValidationError, match="already exists"):
        create_sqlite_snapshot(source, snapshot)
    with pytest.raises(SnapshotValidationError, match="differ"):
        create_sqlite_snapshot(source, source)


def test_snapshot_inspection_rejects_logically_inconsistent_data(tmp_path: Path) -> None:
    source = tmp_path / "inconsistent.db"
    database = Database(source)
    database.initialize()
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO books(id,title,author,publication_year,created_at)
            VALUES (10,'Broken','Writer',2026,'2026-09-06T00:00:00+00:00')
            """
        )
        connection.execute(
            """
            INSERT INTO book_copies(id,book_id,barcode,status,created_at)
            VALUES (20,10,'BROKEN-1','on_loan','2026-09-06T00:00:00+00:00')
            """
        )
        connection.commit()

    with pytest.raises(SnapshotValidationError, match="invalid application state"):
        inspect_sqlite_snapshot(source)


def test_snapshot_inspection_rejects_corruption_and_old_schema(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not sqlite")
    with pytest.raises(SnapshotValidationError, match="validated safely"):
        inspect_sqlite_snapshot(corrupt)

    old = tmp_path / "old.db"
    with sqlite3.connect(old) as connection:
        connection.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO schema_migrations VALUES (1)")
    with pytest.raises(SnapshotValidationError, match="unsupported"):
        inspect_sqlite_snapshot(old)
