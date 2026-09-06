"""Real pg_dump/pg_restore drill inside the local Supabase PostgreSQL container."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from library_management.postgres import PostgresDatabase

pytestmark = pytest.mark.postgres


def test_custom_archive_restores_into_clean_disposable_database(
    pg_database: PostgresDatabase,
    pg_url: str,
    tmp_path: Path,
) -> None:
    container = os.environ.get("LMS_TEST_POSTGRES_CONTAINER")
    if not container:
        pytest.skip("Set LMS_TEST_POSTGRES_CONTAINER to run the native recovery drill.")
    source_name = urlsplit(pg_url).path.lstrip("/")
    target_name = "lms_test_restore_" + uuid4().hex
    with pg_database.transaction() as transaction:
        transaction.connection.execute(
            """
            INSERT INTO users(display_name,username,password_hash,role,created_at)
            VALUES ('Recovery','recovery.user','$argon2id$synthetic','member',now())
            """
        )
        transaction.commit()
    with pg_database.transaction() as transaction:
        source_users = transaction.connection.execute(
            "SELECT username FROM users ORDER BY username"
        ).fetchall()

    dumped = subprocess.run(
        (
            "docker",
            "exec",
            container,
            "pg_dump",
            "-U",
            "postgres",
            "-d",
            source_name,
            "--format=custom",
            "--schema=lms",
            "--no-owner",
            "--no-acl",
        ),
        check=True,
        capture_output=True,
        timeout=60,
    )
    archive = tmp_path / "lms.dump"
    archive.write_bytes(dumped.stdout)
    assert archive.stat().st_size > 0
    assert len(hashlib.sha256(archive.read_bytes()).hexdigest()) == 64

    listed = subprocess.run(
        ("docker", "exec", "-i", container, "pg_restore", "--list"),
        input=dumped.stdout,
        check=True,
        capture_output=True,
        timeout=30,
    )
    assert b"SCHEMA" in listed.stdout
    assert b"TABLE DATA" in listed.stdout

    parsed = urlsplit(pg_url)
    target_url = urlunsplit(parsed._replace(path="/" + target_name))
    with psycopg.connect(pg_url, autocommit=True) as admin:
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(target_name))
        )
        try:
            subprocess.run(
                (
                    "docker",
                    "exec",
                    "-i",
                    container,
                    "pg_restore",
                    "-U",
                    "postgres",
                    "-d",
                    target_name,
                    "--exit-on-error",
                    "--no-owner",
                    "--no-acl",
                ),
                input=dumped.stdout,
                check=True,
                capture_output=True,
                timeout=60,
            )
            with psycopg.connect(target_url) as restored:
                assert restored.execute(
                    "SELECT version FROM lms.schema_version ORDER BY version"
                ).fetchall() == [(1,), (2,), (3,)]
                assert restored.execute(
                    "SELECT username FROM lms.users ORDER BY username"
                ).fetchall() == [(row["username"],) for row in source_users]
                assert ("recovery.user",) in [(row["username"],) for row in source_users]
                assert restored.execute(
                    "SELECT bool_and(rowsecurity) FROM pg_tables WHERE schemaname='lms'"
                ).fetchone() == (True,)
        finally:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(target_name)))
