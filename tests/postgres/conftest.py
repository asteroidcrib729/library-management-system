"""Create a unique disposable database; never reset the local working database."""

import os
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from library_management.postgres import PostgresDatabase, PostgresSettings


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    admin_url = os.environ.get("LMS_TEST_POSTGRES_ADMIN_URL")
    if not admin_url:
        pytest.skip("Set LMS_TEST_POSTGRES_ADMIN_URL to run disposable PostgreSQL tests.")
    PostgresSettings(admin_url, environment="test")
    name = "lms_test_" + uuid4().hex
    # Connect to a loopback admin database, create a new unique test database only.
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=3) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        try:
            connection_string = make_conninfo(admin_url, dbname=name)
            with psycopg.connect(connection_string, autocommit=True) as connection:
                migrations = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
                for migration in sorted(migrations.glob("*.sql")):
                    connection.execute(migration.read_bytes())
            # Keep the URL shape so the application's strict URL validation is exercised.
            parsed = urlsplit(admin_url)
            yield urlunsplit(parsed._replace(path="/" + name))
        finally:
            # name was generated above and never supplied by an external caller.
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture
def pg_database(pg_url: str) -> Iterator[PostgresDatabase]:
    database = PostgresDatabase(PostgresSettings(pg_url, environment="test"))
    database.open()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def migration_database(pg_url: str) -> Iterator[PostgresDatabase]:
    """Create a schema-current empty target dedicated to one import/recovery test."""
    name = "lms_test_migration_" + uuid4().hex
    with psycopg.connect(pg_url, autocommit=True, connect_timeout=3) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        parsed = urlsplit(pg_url)
        connection_string = urlunsplit(parsed._replace(path="/" + name))
        try:
            with psycopg.connect(connection_string, autocommit=True) as connection:
                migrations = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
                for migration in sorted(migrations.glob("*.sql")):
                    connection.execute(migration.read_bytes())
            database = PostgresDatabase(PostgresSettings(connection_string, environment="test"))
            database.open()
            try:
                yield database
            finally:
                database.close()
        finally:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
