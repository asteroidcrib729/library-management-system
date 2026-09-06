import subprocess
from pathlib import Path
from typing import Any

from library_management.postgres import PostgresSettings
from library_management.postgres.recovery import PostgresLogicalRecovery


def test_logical_backup_uses_environment_credentials_and_verifies_archive(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, str]]] = []

    def run(arguments: tuple[str, ...], **options: Any) -> subprocess.CompletedProcess[str]:
        environment = options["env"]
        calls.append((arguments, environment))
        output = next(
            (item.removeprefix("--file=") for item in arguments if item.startswith("--file=")), None
        )
        if output is not None:
            Path(output).write_bytes(b"synthetic custom archive")
            stdout = ""
        else:
            stdout = "; archive listing\n1; 0 0 SCHEMA - lms postgres\n"
        return subprocess.CompletedProcess(arguments, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    settings = PostgresSettings(
        "postgresql://operator:top-secret@127.0.0.1:55432/library",
        environment="test",
    )
    artifact = PostgresLogicalRecovery(settings).create_backup(tmp_path / "backup.dump")

    assert artifact.size_bytes > 0
    assert artifact.listing_entries == 1
    assert len(artifact.sha256) == 64
    assert len(calls) == 2
    for arguments, environment in calls:
        command = " ".join(arguments)
        assert "top-secret" not in command
        assert "postgresql://" not in command
        assert environment["PGPASSWORD"] == "top-secret"
        assert environment["PGDATABASE"] == "library"
