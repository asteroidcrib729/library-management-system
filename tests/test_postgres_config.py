from collections.abc import Callable

import pytest

from library_management.postgres import PostgresDatabase, PostgresSettings

LOCAL_URL = "postgresql://postgres:hidden@127.0.0.1:55432/postgres"


def test_pool_construction_is_closed_and_does_not_reveal_password() -> None:
    settings = PostgresSettings(LOCAL_URL)
    database = PostgresDatabase(settings)
    assert database.pool.closed
    assert database.pool.get_stats()["pool_size"] == 0
    assert "hidden" not in repr(settings)


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///tmp/file",
        "postgresql://user:secret@remote.example/db",
        LOCAL_URL + "?host=remote.example",
        LOCAL_URL + "?options=-csearch_path=public",
        LOCAL_URL + "?sslmode=require&sslmode=disable",
    ],
)
def test_local_database_rejects_remote_and_override_urls(url: str) -> None:
    with pytest.raises(ValueError):
        PostgresSettings(url)


def test_hosted_connections_require_tls() -> None:
    with pytest.raises(ValueError, match="requires sslmode"):
        PostgresSettings("postgresql://user:secret@remote.example/db", environment="production")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PostgresSettings(LOCAL_URL, max_size=0),
        lambda: PostgresSettings(LOCAL_URL, max_waiting=0),
        lambda: PostgresSettings(LOCAL_URL, acquire_timeout=0),
        lambda: PostgresSettings(LOCAL_URL, lock_timeout_ms=0),
        lambda: PostgresSettings(LOCAL_URL, idle_transaction_timeout_ms=1),
    ],
)
def test_unbounded_or_inconsistent_pool_settings_fail(
    factory: Callable[[], PostgresSettings],
) -> None:
    with pytest.raises(ValueError):
        factory()
