"""Atomic, fresh-target-only SQLite-to-PostgreSQL importer."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, LiteralString

from psycopg import sql

from library_management.migration.errors import (
    DataMigrationError,
    ReconciliationError,
    TargetNotEmptyError,
)
from library_management.migration.schema import (
    POSTGRES_SCHEMA_VERSIONS,
    TABLE_COLUMNS,
    canonical_digest,
    rows_as_parameters,
)
from library_management.migration.snapshot import (
    SnapshotInspection,
    inspect_sqlite_snapshot,
)
from library_management.postgres import PostgresDatabase
from library_management.postgres.database import PostgresTransaction
from library_management.repositories import PersistenceError

INSERT_ORDER = tuple(TABLE_COLUMNS)


@dataclass(frozen=True, slots=True)
class ImportReport:
    dry_run: bool
    source_path: Path
    source_file_sha256: str
    row_counts: dict[str, int]
    row_digests: dict[str, str]
    metrics: dict[str, int]

    @property
    def total_rows(self) -> int:
        return sum(self.row_counts.values())


class SqlitePostgresImporter:
    """Copy one validated snapshot into one empty target in a single transaction."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def run(self, snapshot_path: Path, *, dry_run: bool = True) -> ImportReport:
        inspection = inspect_sqlite_snapshot(snapshot_path)
        source_rows = _read_source_rows(inspection.path)
        if _file_digest(inspection.path) != inspection.file_sha256:
            raise DataMigrationError("SQLite snapshot changed after validation.")
        try:
            with self._database.transaction() as transaction:
                transaction.connection.execute("SELECT pg_advisory_xact_lock(1279873875, 200)")
                transaction.connection.execute(
                    """
                    LOCK TABLE users, books, book_copies, reservations, loans, fines,
                               fine_settlements, book_requests, feedback,
                               idempotency_records, browser_sessions IN ACCESS EXCLUSIVE MODE
                    """
                )
                self._assert_compatible_empty_target(transaction)
                self._insert(transaction, source_rows)
                self._reset_sequences(transaction)
                self._reconcile(transaction, inspection)
                report = ImportReport(
                    dry_run=dry_run,
                    source_path=inspection.path,
                    source_file_sha256=inspection.file_sha256,
                    row_counts=dict(inspection.row_counts),
                    row_digests=dict(inspection.row_digests),
                    metrics=dict(inspection.metrics),
                )
                if dry_run:
                    transaction.rollback()
                else:
                    transaction.commit()
                return report
        except DataMigrationError:
            raise
        except PersistenceError as error:
            raise DataMigrationError("PostgreSQL rejected the migration transaction.") from error

    @staticmethod
    def _assert_compatible_empty_target(transaction: PostgresTransaction) -> None:
        versions = tuple(
            int(row["version"])
            for row in transaction.connection.execute(
                "SELECT version FROM schema_version ORDER BY version"
            ).fetchall()
        )
        if versions != POSTGRES_SCHEMA_VERSIONS:
            raise DataMigrationError("PostgreSQL schema is incomplete or unsupported.")
        for table in (*INSERT_ORDER, "idempotency_records", "browser_sessions"):
            query = sql.SQL("SELECT 1 FROM {} LIMIT 1").format(sql.Identifier(table))
            if transaction.connection.execute(query).fetchone() is not None:
                raise TargetNotEmptyError(
                    "PostgreSQL target contains application data; import was refused."
                )

    @staticmethod
    def _insert(
        transaction: PostgresTransaction,
        source_rows: dict[str, list[sqlite3.Row]],
    ) -> None:
        for table in INSERT_ORDER:
            rows = source_rows[table]
            if not rows:
                continue
            columns = TABLE_COLUMNS[table]
            query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            )
            with transaction.connection.cursor() as cursor:
                cursor.executemany(query, rows_as_parameters(table, rows))

    @staticmethod
    def _reset_sequences(transaction: PostgresTransaction) -> None:
        for table in INSERT_ORDER:
            query = sql.SQL(
                "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                "coalesce(max(id), 1), max(id) IS NOT NULL) FROM {}"
            ).format(sql.Identifier(table))
            transaction.connection.execute(
                query,
                (f"lms.{table}",),
            )

    @staticmethod
    def _reconcile(
        transaction: PostgresTransaction,
        source: SnapshotInspection,
    ) -> None:
        target_counts: dict[str, int] = {}
        target_digests: dict[str, str] = {}
        for table, columns in TABLE_COLUMNS.items():
            query = sql.SQL("SELECT {} FROM {} ORDER BY id").format(
                sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                sql.Identifier(table),
            )
            rows = transaction.connection.execute(query).fetchall()
            target_counts[table] = len(rows)
            target_digests[table] = canonical_digest(table, rows)
        target_metrics = _target_metrics(transaction)
        if (
            target_counts != source.row_counts
            or target_digests != source.row_digests
            or target_metrics != source.metrics
        ):
            raise ReconciliationError("SQLite and PostgreSQL reconciliation did not match.")


def _read_source_rows(path: Path) -> dict[str, list[sqlite3.Row]]:
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        result: dict[str, list[sqlite3.Row]] = {}
        for table, columns in TABLE_COLUMNS.items():
            result[table] = connection.execute(
                f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
            ).fetchall()
        return result
    finally:
        connection.close()


def _target_metrics(transaction: PostgresTransaction) -> dict[str, int]:
    statements: tuple[tuple[str, LiteralString], ...] = (
        ("active_loans", "SELECT count(*) AS value FROM loans WHERE returned_at IS NULL"),
        (
            "active_reservations",
            "SELECT count(*) AS value FROM reservations WHERE status='active'",
        ),
        (
            "outstanding_fines",
            "SELECT count(*) AS value FROM fines WHERE status='outstanding'",
        ),
        (
            "outstanding_fine_minor",
            "SELECT coalesce(sum(amount_minor),0) AS value FROM fines WHERE status='outstanding'",
        ),
        (
            "settlement_minor",
            "SELECT coalesce(sum(amount_minor),0) AS value FROM fine_settlements",
        ),
    )
    metrics: dict[str, int] = {}
    for name, statement in statements:
        row: dict[str, Any] | None = transaction.connection.execute(statement).fetchone()
        if row is None:
            raise ReconciliationError("PostgreSQL metric query returned no result.")
        metrics[name] = int(row["value"])
    return metrics


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
