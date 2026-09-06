"""PostgreSQL repository parity, pagination, idempotency, and business races."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial
from threading import Barrier
from typing import Any

import pytest

from library_management.domain import (
    Book,
    BookCopy,
    BookRequest,
    Feedback,
    Fine,
    FineSettlement,
    FineSettlementKind,
    FineStatus,
    Loan,
    RequestStatus,
    Reservation,
    ReservationStatus,
    User,
    UserRole,
)
from library_management.postgres import PostgresDatabase
from library_management.repositories.postgres import PostgresUnitOfWork
from library_management.repositories.postgres.idempotency import (
    IdempotencyConflictError,
    IdempotencyDecision,
)
from library_management.services import (
    CirculationPolicy,
    CirculationService,
    CopyUnavailableError,
    EngagementService,
    FinancialService,
    FineSettlementError,
    InvalidSubmissionTransitionError,
    ReservationConflictError,
)

pytestmark = pytest.mark.postgres
NOW = datetime.now(UTC).replace(microsecond=0)


def add_user(
    database: PostgresDatabase,
    username: str,
    role: UserRole = UserRole.MEMBER,
) -> User:
    with PostgresUnitOfWork(database) as unit_of_work:
        saved = unit_of_work.users.add(
            User(
                display_name=username,
                username=username,
                password_hash="$argon2id$synthetic",
                role=role,
                created_at=NOW,
            )
        )
        unit_of_work.commit()
    return saved


def add_book_copy(database: PostgresDatabase, suffix: str) -> tuple[Book, BookCopy]:
    with PostgresUnitOfWork(database) as unit_of_work:
        book = unit_of_work.books.add(
            Book(title=f"Concurrency {suffix}", author="Test Author", publication_year=2026)
        )
        assert book.id is not None
        copy = unit_of_work.book_copies.add(BookCopy(book_id=book.id, barcode=f"COPY-{suffix}"))
        unit_of_work.commit()
    return book, copy


def run_together(first: Any, second: Any) -> list[object]:
    barrier = Barrier(2)

    def invoke(operation: Any) -> object:
        barrier.wait()
        try:
            return operation()
        except Exception as error:  # Results intentionally include the losing domain conflict.
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(invoke, operation) for operation in (first, second)]
        return [future.result(timeout=10) for future in futures]


def test_all_postgres_repositories_round_trip(pg_database: PostgresDatabase) -> None:
    member = add_user(pg_database, "repo.member")
    staff = add_user(pg_database, "repo.staff", UserRole.LIBRARIAN)
    assert member.id is not None and staff.id is not None
    book, copy = add_book_copy(pg_database, "REPO")
    assert book.id is not None and copy.id is not None

    with PostgresUnitOfWork(pg_database) as uow:
        reservation = uow.reservations.add(
            Reservation(user_id=member.id, book_id=book.id, created_at=NOW)
        )
        assert reservation.id is not None
        uow.reservations.resolve(reservation.id, ReservationStatus.CANCELLED, NOW)
        loan = uow.loans.add(
            Loan(
                user_id=member.id,
                book_copy_id=copy.id,
                checked_out_at=NOW,
                due_at=NOW + timedelta(days=14),
            )
        )
        assert loan.id is not None
        fine = uow.fines.add(
            Fine(
                user_id=member.id,
                loan_id=loan.id,
                reason="Synthetic overdue fine",
                amount=Decimal("12.34"),
                assessed_at=NOW,
            )
        )
        assert fine.id is not None
        uow.fines.settle(fine.id, FineStatus.PAID, NOW)
        settlement = uow.fine_settlements.add(
            FineSettlement(
                fine_id=fine.id,
                recorded_by_user_id=staff.id,
                kind=FineSettlementKind.PAYMENT,
                amount=fine.amount,
                created_at=NOW,
            )
        )
        request = uow.book_requests.add(
            BookRequest(user_id=member.id, title="Requested", author="Writer", created_at=NOW)
        )
        assert request.id is not None
        uow.book_requests.review(request.id, RequestStatus.APPROVED, staff.id, NOW, None)
        uow.book_requests.mark_acquired(request.id, book.id, staff.id, NOW)
        feedback = uow.feedback.add(Feedback(user_id=member.id, content="Useful", created_at=NOW))
        assert feedback.id is not None
        uow.feedback.update_status(
            feedback.id,
            feedback.status,
            feedback.status.REVIEWED,
            staff.id,
            NOW,
        )
        assert uow.reporting.count_active_users() >= 2
        assert uow.reporting.count_titles() >= 1
        assert uow.reporting.outstanding_fines()[0] == 0
        assert settlement.id is not None
        uow.commit()

    with PostgresUnitOfWork(pg_database) as uow:
        assert uow.fine_settlements.get_for_fine(fine.id) == settlement
        assert uow.book_requests.get_by_id(request.id).status is RequestStatus.ACQUIRED  # type: ignore[union-attr]
        assert uow.feedback.get_by_id(feedback.id).status.value == "reviewed"  # type: ignore[union-attr]


def test_catalog_keyset_pagination_and_index_plan(pg_database: PostgresDatabase) -> None:
    with PostgresUnitOfWork(pg_database) as uow:
        for number in range(125):
            uow.books.add(Book(title=f"Page {number:03}", author="Paging", publication_year=2026))
        uow.commit()

    identifiers: list[int] = []
    cursor = None
    with PostgresUnitOfWork(pg_database) as uow:
        while True:
            page = uow.books.search_page("Page", limit=37, after=cursor)
            identifiers.extend(book.id or 0 for book in page.items)
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
        assert len(identifiers) == 125
        assert len(set(identifiers)) == 125
        assert uow.books.search("100%_missing") == []
        connection = uow._active_transaction().connection
        connection.execute("SET LOCAL enable_seqscan=off")
        rows = connection.execute(
            "EXPLAIN SELECT * FROM books WHERE (lower(title), id) > ('page 050', 0) "
            "ORDER BY lower(title), id LIMIT 25"
        ).fetchall()
        assert "books_page_idx" in "\n".join(str(row["QUERY PLAN"]) for row in rows)


def test_idempotency_claim_replay_mismatch_and_stale_takeover(
    pg_database: PostgresDatabase,
) -> None:
    actor = add_user(pg_database, "idempotent.member")
    assert actor.id is not None
    digest = "a" * 64
    expiry = NOW + timedelta(minutes=5)
    with PostgresUnitOfWork(pg_database) as uow:
        result = uow.idempotency.claim(
            actor_id=actor.id,
            operation="checkout",
            key="key-1",
            request_hash=digest,
            owner_token="owner-1",
            now=NOW,
            expires_at=expiry,
        )
        assert result.decision is IdempotencyDecision.CLAIMED
        uow.commit()
    with PostgresUnitOfWork(pg_database) as uow:
        assert (
            uow.idempotency.claim(
                actor_id=actor.id,
                operation="checkout",
                key="key-1",
                request_hash=digest,
                owner_token="owner-2",
                now=NOW,
                expires_at=expiry,
            ).decision
            is IdempotencyDecision.IN_PROGRESS
        )
    with pytest.raises(IdempotencyConflictError), PostgresUnitOfWork(pg_database) as uow:
        uow.idempotency.complete(
            actor_id=actor.id,
            operation="checkout",
            key="key-1",
            owner_token="not-the-owner",
            response={"loan_id": 1},
            response_status=201,
        )
    with pytest.raises(IdempotencyConflictError), PostgresUnitOfWork(pg_database) as uow:
        uow.idempotency.claim(
            actor_id=actor.id,
            operation="checkout",
            key="key-1",
            request_hash="b" * 64,
            owner_token="owner-2",
            now=NOW,
            expires_at=expiry,
        )
    with PostgresUnitOfWork(pg_database) as uow:
        assert (
            uow.idempotency.claim(
                actor_id=actor.id,
                operation="checkout",
                key="key-1",
                request_hash=digest,
                owner_token="owner-2",
                now=expiry,
                expires_at=expiry + timedelta(minutes=5),
            ).decision
            is IdempotencyDecision.CLAIMED
        )
        uow.idempotency.complete(
            actor_id=actor.id,
            operation="checkout",
            key="key-1",
            owner_token="owner-2",
            response={"loan_id": 42},
            response_status=201,
        )
        uow.commit()
    with PostgresUnitOfWork(pg_database) as uow:
        replay = uow.idempotency.claim(
            actor_id=actor.id,
            operation="checkout",
            key="key-1",
            request_hash=digest,
            owner_token="owner-3",
            now=expiry,
            expires_at=expiry + timedelta(minutes=5),
        )
        assert (replay.decision, replay.response_status, replay.response) == (
            IdempotencyDecision.REPLAY,
            201,
            {"loan_id": 42},
        )


def test_simultaneous_idempotency_claim_has_one_owner(pg_database: PostgresDatabase) -> None:
    actor = add_user(pg_database, "claim.member")
    assert actor.id is not None

    def claim(owner: str) -> IdempotencyDecision:
        with PostgresUnitOfWork(pg_database) as uow:
            result = uow.idempotency.claim(
                actor_id=actor.id or 0,
                operation="return",
                key="simultaneous-key",
                request_hash="c" * 64,
                owner_token=owner,
                now=NOW,
                expires_at=NOW + timedelta(minutes=5),
            )
            uow.commit()
            return result.decision

    results = run_together(lambda: claim("owner-a"), lambda: claim("owner-b"))
    assert results.count(IdempotencyDecision.CLAIMED) == 1
    assert results.count(IdempotencyDecision.IN_PROGRESS) == 1


def test_concurrent_reservation_checkout_return_and_renewal(
    pg_database: PostgresDatabase,
) -> None:
    staff = add_user(pg_database, "race.staff", UserRole.LIBRARIAN)
    member = add_user(pg_database, "race.member")
    book, copy = add_book_copy(pg_database, "RACE")
    assert staff.id and member.id and book.id and copy.id
    factory = partial(PostgresUnitOfWork, pg_database)
    service = CirculationService(
        factory,
        policy=CirculationPolicy(maximum_renewals=2),
        clock=lambda: NOW,
    )

    reservations = run_together(
        lambda: service.reserve(member.id or 0, book.id or 0),
        lambda: service.reserve(member.id or 0, book.id or 0),
    )
    assert sum(isinstance(item, ReservationConflictError) for item in reservations) == 1
    reservation = service.list_reservations(member.id)[0]
    service.cancel_reservation(member.id, reservation.reservation.id or 0)

    checkouts = run_together(
        lambda: service.checkout(staff.id or 0, member.username, copy.barcode),
        lambda: service.checkout(staff.id or 0, member.username, copy.barcode),
    )
    assert sum(isinstance(item, CopyUnavailableError) for item in checkouts) == 1
    loan = next(item.loan for item in checkouts if not isinstance(item, Exception))  # type: ignore[union-attr]

    renewals = run_together(
        lambda: service.renew(member.id or 0, loan.id or 0),
        lambda: service.renew(member.id or 0, loan.id or 0),
    )
    assert not any(isinstance(item, Exception) for item in renewals)
    assert {item.loan.renewal_count for item in renewals} == {1, 2}  # type: ignore[union-attr]

    returns = run_together(
        lambda: service.return_copy(staff.id or 0, copy.barcode),
        lambda: service.return_copy(staff.id or 0, copy.barcode),
    )
    assert sum(isinstance(item, CopyUnavailableError) for item in returns) == 1


def test_concurrent_settlement_and_review_have_one_winner(
    pg_database: PostgresDatabase,
) -> None:
    staff = add_user(pg_database, "decision.staff", UserRole.ADMINISTRATOR)
    member = add_user(pg_database, "decision.member")
    assert staff.id and member.id
    factory = partial(PostgresUnitOfWork, pg_database)
    financial = FinancialService(factory, clock=lambda: NOW)
    fine = financial.assess_manual(staff.id, member.username, Decimal("50.00"), "Damage")
    settlements = run_together(
        lambda: financial.record_payment(staff.id or 0, fine.fine.id or 0),
        lambda: financial.record_payment(staff.id or 0, fine.fine.id or 0),
    )
    assert sum(isinstance(item, FineSettlementError) for item in settlements) == 1

    engagement = EngagementService(factory, clock=lambda: NOW)
    request = engagement.submit_book_request(member.id, "Concurrent", "Reviewer")
    reviews = run_together(
        lambda: engagement.review_book_request(
            staff.id or 0, request.request.id or 0, RequestStatus.APPROVED
        ),
        lambda: engagement.review_book_request(
            staff.id or 0, request.request.id or 0, RequestStatus.REJECTED, "No"
        ),
    )
    assert sum(isinstance(item, InvalidSubmissionTransitionError) for item in reviews) == 1
