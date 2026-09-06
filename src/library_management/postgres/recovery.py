"""Guarded PostgreSQL logical backup and restore boundary."""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import psycopg

from library_management.migration.errors import LogicalRecoveryError
from library_management.postgres.config import PostgresSettings


@dataclass(frozen=True, slots=True)
class LogicalBackupArtifact:
    path: Path
    size_bytes: int
    sha256: str
    listing_entries: int


class PostgresLogicalRecovery:
    """Call supported PostgreSQL client tools without putting credentials in argv."""

    def __init__(
        self,
        settings: PostgresSettings,
        *,
        pg_dump: str = "pg_dump",
        pg_restore: str = "pg_restore",
        timeout_seconds: int = 300,
    ) -> None:
        self._settings = settings
        self._pg_dump = pg_dump
        self._pg_restore = pg_restore
        self._timeout_seconds = timeout_seconds

    def create_backup(self, destination: Path) -> LogicalBackupArtifact:
        destination = destination.resolve()
        if destination.exists():
            raise LogicalRecoveryError("Logical backup destination already exists.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._run(
                (
                    self._pg_dump,
                    "--format=custom",
                    "--no-owner",
                    "--no-acl",
                    "--schema=lms",
                    f"--file={destination}",
                )
            )
            return self.verify_backup(destination)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def verify_backup(self, archive: Path) -> LogicalBackupArtifact:
        archive = archive.resolve()
        if not archive.is_file():
            raise LogicalRecoveryError("Logical backup archive does not exist.")
        result = self._run((self._pg_restore, "--list", str(archive)))
        entries = sum(
            1
            for line in result.stdout.splitlines()
            if line.strip() and not line.lstrip().startswith(";")
        )
        if entries == 0:
            raise LogicalRecoveryError("Logical backup archive contains no restorable entries.")
        return LogicalBackupArtifact(
            path=archive,
            size_bytes=archive.stat().st_size,
            sha256=_file_digest(archive),
            listing_entries=entries,
        )

    def restore_backup(self, archive: Path) -> LogicalBackupArtifact:
        artifact = self.verify_backup(archive)
        try:
            with psycopg.connect(self._settings.url, connect_timeout=5) as connection:
                row = connection.execute("SELECT to_regnamespace('lms')").fetchone()
                if row is None or row[0] is not None:
                    raise LogicalRecoveryError(
                        "Restore target already contains the lms schema; restore was refused."
                    )
            database_name = unquote(urlsplit(self._settings.url).path.lstrip("/"))
            self._run(
                (
                    self._pg_restore,
                    "--exit-on-error",
                    "--no-owner",
                    "--no-acl",
                    f"--dbname={database_name}",
                    str(artifact.path),
                )
            )
            self._validate_restored_database()
        except LogicalRecoveryError:
            raise
        except psycopg.Error as error:
            raise LogicalRecoveryError("Restore target could not be inspected safely.") from error
        return artifact

    def _validate_restored_database(self) -> None:
        try:
            with psycopg.connect(self._settings.url, connect_timeout=5) as connection:
                versions = connection.execute(
                    "SELECT version FROM lms.schema_version ORDER BY version"
                ).fetchall()
                rls = connection.execute(
                    """
                    SELECT count(*), count(*) FILTER (WHERE rowsecurity)
                    FROM pg_tables WHERE schemaname='lms'
                    """
                ).fetchone()
                if (
                    versions != [(1,), (2,), (3,)]
                    or rls is None
                    or rls[0] != rls[1]
                    or rls[0] != 12
                ):
                    raise LogicalRecoveryError(
                        "Restored database failed schema-version or RLS validation."
                    )
        except LogicalRecoveryError:
            raise
        except psycopg.Error as error:
            raise LogicalRecoveryError("Restored database could not be validated.") from error

    def _run(self, arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                arguments,
                check=True,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                env=self._client_environment(),
            )
        except FileNotFoundError as error:
            raise LogicalRecoveryError("Required PostgreSQL client tool was not found.") from error
        except subprocess.TimeoutExpired as error:
            raise LogicalRecoveryError(
                "PostgreSQL recovery command exceeded its timeout."
            ) from error
        except subprocess.CalledProcessError as error:
            raise LogicalRecoveryError("PostgreSQL recovery command failed.") from error

    def _client_environment(self) -> dict[str, str]:
        parsed = urlsplit(self._settings.url)
        query = parse_qs(parsed.query)
        environment = os.environ.copy()
        environment.update(
            {
                "PGHOST": parsed.hostname or "",
                "PGPORT": str(parsed.port or 5432),
                "PGUSER": unquote(parsed.username or ""),
                "PGDATABASE": unquote(parsed.path.lstrip("/")),
                "PGSSLMODE": query.get("sslmode", ["prefer"])[0],
            }
        )
        if parsed.password is not None:
            environment["PGPASSWORD"] = unquote(parsed.password)
        else:
            environment.pop("PGPASSWORD", None)
        return environment


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
