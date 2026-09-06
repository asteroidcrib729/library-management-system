"""Guarded operator commands for SQLite import and PostgreSQL recovery."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from library_management.migration import (
    SqlitePostgresImporter,
    create_sqlite_snapshot,
    inspect_sqlite_snapshot,
)
from library_management.migration.errors import DataMigrationError
from library_management.postgres import PostgresDatabase, PostgresSettings
from library_management.postgres.recovery import PostgresLogicalRecovery


def _database_settings(arguments: argparse.Namespace) -> PostgresSettings:
    url = os.environ.get(arguments.database_url_env)
    if not url:
        raise DataMigrationError(
            f"Required database URL environment variable {arguments.database_url_env} is unset."
        )
    return PostgresSettings(url, environment=arguments.environment)


def _recovery(arguments: argparse.Namespace) -> PostgresLogicalRecovery:
    return PostgresLogicalRecovery(
        _database_settings(arguments),
        pg_dump=os.environ.get("LMS_PG_DUMP", "pg_dump"),
        pg_restore=os.environ.get("LMS_PG_RESTORE", "pg_restore"),
    )


def _payload(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return {name: _payload(getattr(value, name)) for name in value.__dataclass_fields__}
    if isinstance(value, dict):
        return {str(key): _payload(item) for key, item in value.items()}
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    snapshot = commands.add_parser("snapshot", help="create a validated SQLite snapshot")
    snapshot.add_argument("--source", type=Path, required=True)
    snapshot.add_argument("--output", type=Path, required=True)

    inspect = commands.add_parser("inspect", help="validate and summarize a SQLite snapshot")
    inspect.add_argument("--snapshot", type=Path, required=True)

    import_command = commands.add_parser("import", help="import into an empty PostgreSQL target")
    import_command.add_argument("--snapshot", type=Path, required=True)
    import_command.add_argument("--commit", action="store_true", help="commit after reconciliation")
    _add_database_options(import_command)

    backup = commands.add_parser("backup", help="create and verify a logical archive")
    backup.add_argument("--output", type=Path, required=True)
    _add_database_options(backup)

    verify = commands.add_parser("verify-backup", help="list and hash a logical archive")
    verify.add_argument("--archive", type=Path, required=True)
    _add_database_options(verify)

    restore = commands.add_parser("restore", help="restore only into a schema-empty database")
    restore.add_argument("--archive", type=Path, required=True)
    _add_database_options(restore)
    return parser


def _add_database_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--database-url-env", default="DATABASE_URL")
    parser.add_argument(
        "--environment",
        choices=("local", "test", "preview", "staging", "production"),
        default="local",
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "snapshot":
            result = create_sqlite_snapshot(arguments.source, arguments.output)
        elif arguments.command == "inspect":
            result = inspect_sqlite_snapshot(arguments.snapshot)
        elif arguments.command == "import":
            database = PostgresDatabase(_database_settings(arguments))
            database.open()
            try:
                result = SqlitePostgresImporter(database).run(
                    arguments.snapshot, dry_run=not arguments.commit
                )
            finally:
                database.close()
        elif arguments.command == "backup":
            result = _recovery(arguments).create_backup(arguments.output)
        elif arguments.command == "verify-backup":
            result = _recovery(arguments).verify_backup(arguments.archive)
        elif arguments.command == "restore":
            result = _recovery(arguments).restore_backup(arguments.archive)
        else:
            raise AssertionError("Unknown migration command.")
    except (DataMigrationError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    print(json.dumps({"ok": True, "result": _payload(result)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
