from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from typing import LiteralString
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from library_management.api import create_app
from library_management.api.config import ApiSettings, Environment
from library_management.postgres import PostgresDatabase, PostgresTransaction
from library_management.postgres.database import RetryableTransactionError, TransactionBusyError
from library_management.repositories import (
    DuplicateRecordError,
    PersistenceError,
    RecordNotFoundError,
)

pytestmark = pytest.mark.postgres


def add_user(transaction: PostgresTransaction) -> int:
    row = transaction.connection.execute(
        "INSERT INTO lms.users(display_name, username, password_hash, role, created_at) "
        "VALUES ('Test', %s, 'synthetic-hash', 'member', now()) RETURNING id",
        ("u" + uuid4().hex[:20],),
    ).fetchone()
    assert row is not None
    return row["id"]


def test_commit_rollback_and_connection_return(pg_database: PostgresDatabase) -> None:
    with pg_database.transaction() as transaction:
        rolled_back = add_user(transaction)
    with pg_database.transaction() as transaction:
        assert (
            transaction.connection.execute(
                "SELECT id FROM lms.users WHERE id=%s", (rolled_back,)
            ).fetchone()
            is None
        )
    with pg_database.transaction() as transaction:
        committed = add_user(transaction)
        transaction.commit()
        with pytest.raises(RuntimeError):
            _ = transaction.connection
    with pg_database.transaction() as transaction:
        assert (
            transaction.connection.execute(
                "SELECT id FROM lms.users WHERE id=%s", (committed,)
            ).fetchone()
            is not None
        )
    assert pg_database.pool.get_stats().get("requests_waiting", 0) == 0


def test_failed_statement_returns_usable_connection(pg_database: PostgresDatabase) -> None:
    with pytest.raises(psycopg.errors.DivisionByZero), pg_database.transaction() as transaction:
        transaction.connection.execute("SELECT 1/0")
    assert pg_database.schema_ready()


def test_pool_exhaustion_is_bounded(pg_database: PostgresDatabase) -> None:
    database = PostgresDatabase(replace(pg_database.settings, max_size=1, acquire_timeout=0.15))
    database.open()
    try:
        with database.transaction(), pytest.raises(TransactionBusyError), database.transaction():
            pytest.fail("Exhausted pool unexpectedly supplied a connection")
        assert database.schema_ready()
        assert database.pool.get_stats()["pool_size"] <= 1
    finally:
        database.close()


def test_lock_timeout_and_reads_during_write(pg_database: PostgresDatabase) -> None:
    user_id = pg_database.run(add_user)
    contender = PostgresDatabase(replace(pg_database.settings, lock_timeout_ms=100))
    contender.open()
    try:
        with pg_database.transaction() as writer:
            writer.connection.execute(
                "UPDATE lms.users SET display_name='Pending' WHERE id=%s", (user_id,)
            )
            with contender.transaction() as reader:
                row = reader.connection.execute(
                    "SELECT display_name FROM lms.users WHERE id=%s", (user_id,)
                ).fetchone()
                assert row == {"display_name": "Test"}
            with pytest.raises(TransactionBusyError), contender.transaction() as blocked:
                blocked.connection.execute(
                    "UPDATE lms.users SET display_name='Blocked' WHERE id=%s", (user_id,)
                )
        assert contender.schema_ready()
    finally:
        contender.close()


def test_statement_timeout_is_rolled_back(pg_database: PostgresDatabase) -> None:
    database = PostgresDatabase(
        replace(pg_database.settings, lock_timeout_ms=50, statement_timeout_ms=100)
    )
    database.open()
    try:
        with pytest.raises(TransactionBusyError), database.transaction() as transaction:
            transaction.connection.execute("SELECT pg_sleep(1)")
        assert database.schema_ready()
    finally:
        database.close()


def test_actual_deadlock_retries_complete_transaction(pg_database: PostgresDatabase) -> None:
    first, second = pg_database.run(add_user), pg_database.run(add_user)
    barrier = Barrier(2)

    def worker(order: tuple[int, int]) -> int:
        attempts = 0

        def command(transaction: PostgresTransaction) -> None:
            nonlocal attempts
            attempts += 1
            transaction.connection.execute(
                "SELECT id FROM lms.users WHERE id=%s FOR UPDATE", (order[0],)
            )
            if attempts == 1:
                barrier.wait(timeout=5)
            transaction.connection.execute(
                "SELECT id FROM lms.users WHERE id=%s FOR UPDATE", (order[1],)
            )
            transaction.connection.execute(
                "UPDATE lms.users SET display_name='Completed' WHERE id=%s", (order[0],)
            )

        pg_database.run(command)
        return attempts

    with ThreadPoolExecutor(max_workers=2) as executor:
        left = executor.submit(worker, (first, second))
        right = executor.submit(worker, (second, first))
        attempts = [left.result(timeout=10), right.result(timeout=10)]
    assert sorted(attempts) == [1, 2]
    assert pg_database.schema_ready()


def test_retry_exhaustion_stops_after_three_attempts(pg_database: PostgresDatabase) -> None:
    attempts = 0

    def command(transaction: PostgresTransaction) -> None:
        nonlocal attempts
        attempts += 1
        add_user(transaction)
        transaction.connection.execute(
            "DO $$ BEGIN RAISE EXCEPTION 'synthetic abort' USING ERRCODE='40001'; END $$"
        )

    with pytest.raises(RetryableTransactionError):
        pg_database.run(command)
    assert attempts == 3
    assert pg_database.schema_ready()


def test_api_lifespan_and_schema_readiness(pg_url: str) -> None:
    app = create_app(ApiSettings(environment=Environment.TEST, database_url=pg_url))
    assert app.state.database.pool.closed
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200
    assert app.state.database.pool.closed


def test_readiness_rejects_future_schema(pg_database: PostgresDatabase) -> None:
    try:
        with pg_database.transaction() as transaction:
            transaction.connection.execute("INSERT INTO lms.schema_version VALUES (999, now())")
            transaction.commit()
        assert not pg_database.schema_ready()
    finally:
        with pg_database.transaction() as transaction:
            transaction.connection.execute("DELETE FROM lms.schema_version WHERE version=999")
            transaction.commit()


def test_unique_username_and_pending_request_null_year(pg_database: PostgresDatabase) -> None:
    user_id = pg_database.run(add_user)
    with pg_database.transaction() as transaction:
        transaction.connection.execute(
            "INSERT INTO lms.book_requests(user_id,title,author,status,created_at) "
            "VALUES (%s,'Same title','Same author','pending',now())",
            (user_id,),
        )
        transaction.commit()
    with pytest.raises(DuplicateRecordError), pg_database.transaction() as transaction:
        transaction.connection.execute(
            "INSERT INTO lms.book_requests(user_id,title,author,status,created_at) "
            "VALUES (%s,'SAME TITLE','same author','pending',now())",
            (user_id,),
        )


def test_money_checks_and_foreign_keys(pg_database: PostgresDatabase) -> None:
    user_id = pg_database.run(add_user)
    with (
        pytest.raises(PersistenceError, match="invalid record state"),
        pg_database.transaction() as transaction,
    ):
        transaction.connection.execute(
            "INSERT INTO lms.fines(user_id,reason,amount_minor,status,assessed_at) "
            "VALUES (%s,'Synthetic',0,'outstanding',now())",
            (user_id,),
        )
    with (
        pytest.raises(RecordNotFoundError),
        pg_database.transaction() as transaction,
    ):
        transaction.connection.execute(
            "INSERT INTO lms.fines(user_id,reason,amount_minor,status,assessed_at) "
            "VALUES (-1,'Synthetic',100,'outstanding',now())"
        )


def test_all_app_tables_have_rls(pg_database: PostgresDatabase) -> None:
    with pg_database.transaction() as transaction:
        rows = transaction.connection.execute(
            "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='lms'"
        ).fetchall()
    assert len(rows) == 12
    assert all(row["rowsecurity"] for row in rows)


def test_active_loan_reservation_and_settlement_uniqueness(pg_database: PostgresDatabase) -> None:
    with pg_database.transaction() as transaction:
        user_id = add_user(transaction)
        book = transaction.connection.execute(
            "INSERT INTO lms.books(title,author,publication_year,created_at) "
            "VALUES (%s,'Test',2020,now()) RETURNING id",
            (uuid4().hex,),
        ).fetchone()
        assert book is not None
        copy = transaction.connection.execute(
            "INSERT INTO lms.book_copies(book_id,barcode,status,created_at) "
            "VALUES (%s,%s,'available',now()) RETURNING id",
            (book["id"], uuid4().hex.upper()),
        ).fetchone()
        assert copy is not None
        loan = transaction.connection.execute(
            "INSERT INTO lms.loans(user_id,book_copy_id,checked_out_at,due_at) "
            "VALUES (%s,%s,now(),now()+interval '14 days') RETURNING id",
            (user_id, copy["id"]),
        ).fetchone()
        assert loan is not None
        fine = transaction.connection.execute(
            "INSERT INTO lms.fines(user_id,loan_id,reason,amount_minor,status,assessed_at) "
            "VALUES (%s,%s,'Test',100,'outstanding',now()) RETURNING id",
            (user_id, loan["id"]),
        ).fetchone()
        assert fine is not None
        transaction.connection.execute(
            "INSERT INTO lms.reservations(user_id,book_id,status,created_at) "
            "VALUES (%s,%s,'active',now())",
            (user_id, book["id"]),
        )
        transaction.connection.execute(
            "UPDATE lms.fines SET status='paid',settled_at=now() WHERE id=%s", (fine["id"],)
        )
        transaction.connection.execute(
            "INSERT INTO lms.fine_settlements("
            "fine_id,recorded_by_user_id,kind,amount_minor,created_at) "
            "VALUES (%s,%s,'payment',100,now())",
            (fine["id"], user_id),
        )
        transaction.commit()
    statements: list[tuple[LiteralString, tuple[int, int]]] = [
        (
            "INSERT INTO lms.loans(user_id,book_copy_id,checked_out_at,due_at) "
            "VALUES (%s,%s,now(),now()+interval '14 days')",
            (user_id, copy["id"]),
        ),
        (
            "INSERT INTO lms.reservations(user_id,book_id,status,created_at) "
            "VALUES (%s,%s,'active',now())",
            (user_id, book["id"]),
        ),
        (
            "INSERT INTO lms.fines(user_id,loan_id,reason,amount_minor,status,assessed_at) "
            "VALUES (%s,%s,'Duplicate',100,'outstanding',now())",
            (user_id, loan["id"]),
        ),
        (
            "INSERT INTO lms.fine_settlements("
            "fine_id,recorded_by_user_id,kind,amount_minor,created_at) "
            "VALUES (%s,%s,'payment',100,now())",
            (fine["id"], user_id),
        ),
    ]
    for statement, parameters in statements:
        with (
            pytest.raises(DuplicateRecordError),
            pg_database.transaction() as transaction,
        ):
            transaction.connection.execute(statement, parameters)


def test_no_retry_on_connection_loss(pg_database: PostgresDatabase) -> None:
    from library_management.postgres.database import DatabaseUnavailableError

    attempts = 0

    def command(transaction: PostgresTransaction) -> None:
        nonlocal attempts
        attempts += 1
        transaction.connection.close()
        transaction.connection.execute("SELECT 1")

    with pytest.raises(DatabaseUnavailableError):
        pg_database.run(command)
    assert attempts == 1
    assert pg_database.schema_ready()


def test_nested_transaction_reuse_is_rejected(pg_database: PostgresDatabase) -> None:
    with pg_database.transaction() as transaction:
        with pytest.raises(RuntimeError, match="already active"):
            transaction.__enter__()
        assert transaction.connection.execute("SELECT 1").fetchone() is not None


def test_missing_schema_is_unready_without_startup_migration(pg_url: str) -> None:
    # Temporarily rename the marker in this exclusively owned disposable database.
    with psycopg.connect(pg_url, autocommit=True) as connection:
        connection.execute("ALTER TABLE lms.schema_version RENAME TO hidden_version")
        try:
            app = create_app(ApiSettings(environment=Environment.TEST, database_url=pg_url))
            with TestClient(app) as client:
                assert client.get("/health/live").status_code == 200
                response = client.get("/health/ready")
                assert response.status_code == 503
                assert "hidden_version" not in response.text
                assert "postgres:postgres" not in response.text
            assert connection.execute("SELECT to_regclass('lms.schema_version')").fetchone() == (
                None,
            )
        finally:
            connection.execute("ALTER TABLE lms.hidden_version RENAME TO schema_version")
