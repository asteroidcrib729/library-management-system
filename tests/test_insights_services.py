from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import partial

import pytest

from library_management.database import Database
from library_management.domain import (
    Book,
    BookCopy,
    BookCopyStatus,
    BookRequest,
    Feedback,
    Fine,
    Loan,
    Reservation,
    User,
    UserRole,
)
from library_management.repositories import UnitOfWork
from library_management.repositories.sqlite import SqliteUnitOfWork
from library_management.services import (
    AuthorizationError,
    InsightsService,
    InvalidResultLimitError,
)

NOW = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)


def build_factory(database: Database) -> Callable[[], UnitOfWork]:
    return partial(SqliteUnitOfWork, database)


def build_service(database: Database) -> InsightsService:
    return InsightsService(build_factory(database), clock=lambda: NOW)


def add_user(database: Database, username: str, role: UserRole = UserRole.MEMBER) -> User:
    with SqliteUnitOfWork(database) as unit_of_work:
        user = unit_of_work.users.add(
            User(
                display_name=username,
                username=username,
                password_hash="$argon2id$test-hash",
                role=role,
            )
        )
        unit_of_work.commit()
    return user


def add_book(
    database: Database,
    title: str,
    author: str,
    category: str,
    *,
    available_copies: int = 1,
    unavailable_copies: int = 0,
) -> tuple[Book, list[BookCopy]]:
    with SqliteUnitOfWork(database) as unit_of_work:
        book = unit_of_work.books.add(
            Book(
                title=title,
                author=author,
                publication_year=2000,
                category=category,
            )
        )
        copies = [
            unit_of_work.book_copies.add(
                BookCopy(book_id=book.id or 0, barcode=f"{title[:3].upper()}-A-{index}")
            )
            for index in range(available_copies)
        ]
        copies.extend(
            unit_of_work.book_copies.add(
                BookCopy(
                    book_id=book.id or 0,
                    barcode=f"{title[:3].upper()}-U-{index}",
                    status=BookCopyStatus.DAMAGED,
                )
            )
            for index in range(unavailable_copies)
        )
        unit_of_work.commit()
    return book, copies


def add_returned_loans(database: Database, user: User, copy: BookCopy, count: int) -> None:
    with SqliteUnitOfWork(database) as unit_of_work:
        for index in range(count):
            checked_out = NOW - timedelta(days=30 + index * 20)
            unit_of_work.loans.add(
                Loan(
                    user_id=user.id or 0,
                    book_copy_id=copy.id or 0,
                    checked_out_at=checked_out,
                    due_at=checked_out + timedelta(days=14),
                    returned_at=checked_out + timedelta(days=10),
                )
            )
        unit_of_work.commit()


def test_cold_start_prefers_availability_then_stable_title_order(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    add_book(database, "Beta", "Author B", "General", available_copies=2)
    add_book(database, "Alpha", "Author A", "General")
    add_book(database, "Gamma", "Author C", "General", available_copies=0, unavailable_copies=1)

    first = service.recommend(member.id or 0)
    second = service.recommend(member.id or 0)

    assert [view.book.title for view in first] == ["Beta", "Alpha"]
    assert first == second
    assert all(view.available_copies > 0 for view in first)


def test_personalization_prefers_category_then_author_and_excludes_history(
    database: Database,
) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    other = add_user(database, "reader.two")
    history_book, history_copies = add_book(database, "History", "Favorite Author", "Science")
    add_returned_loans(database, member, history_copies[0], 1)
    category_book, _ = add_book(database, "Category Match", "Other Author", "Science")
    author_book, _ = add_book(database, "Author Match", "Favorite Author", "Drama")
    popular_book, popular_copies = add_book(database, "Popular", "Third Author", "Drama")
    add_returned_loans(database, other, popular_copies[0], 20)

    recommendations = service.recommend(member.id or 0)

    assert [view.book.id for view in recommendations[:3]] == [
        category_book.id,
        author_book.id,
        popular_book.id,
    ]
    assert history_book.id not in {view.book.id for view in recommendations}
    assert recommendations[0].reason == "Matches your interest in Science."


def test_popular_books_rank_checkout_count_and_require_availability(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    popular, popular_copies = add_book(database, "Popular", "Author", "General")
    add_returned_loans(database, member, popular_copies[0], 3)
    add_book(database, "Unpopular", "Another", "General")
    unavailable, unavailable_copies = add_book(
        database, "Unavailable", "Third", "General", available_copies=0, unavailable_copies=1
    )
    add_returned_loans(database, member, unavailable_copies[0], 5)

    results = service.popular(member.id or 0)

    assert results[0].book.id == popular.id
    assert results[0].historical_checkouts == 3
    assert unavailable.id not in {view.book.id for view in results}


@pytest.mark.parametrize("limit", [0, 21])
def test_recommendation_limit_is_bounded(database: Database, limit: int) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")

    with pytest.raises(InvalidResultLimitError, match="between 1 and 20"):
        service.recommend(member.id or 0, limit)


def test_dashboard_requires_staff_and_reports_all_workloads(database: Database) -> None:
    service = build_service(database)
    member = add_user(database, "reader.one")
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    book, copies = add_book(database, "Dune", "Frank Herbert", "Science", available_copies=2)
    with SqliteUnitOfWork(database) as unit_of_work:
        unit_of_work.loans.add(
            Loan(
                user_id=member.id or 0,
                book_copy_id=copies[0].id or 0,
                checked_out_at=NOW - timedelta(days=20),
                due_at=NOW - timedelta(days=6),
            )
        )
        unit_of_work.book_copies.update_status(copies[0].id or 0, BookCopyStatus.ON_LOAN)
        unit_of_work.reservations.add(
            Reservation(user_id=member.id or 0, book_id=book.id or 0, created_at=NOW)
        )
        unit_of_work.fines.add(
            Fine(
                user_id=member.id or 0,
                reason="Overdue",
                amount=Decimal("12.34"),
                assessed_at=NOW,
            )
        )
        unit_of_work.book_requests.add(
            BookRequest(user_id=member.id or 0, title="Foundation", author="Isaac Asimov")
        )
        unit_of_work.feedback.add(Feedback(user_id=member.id or 0, content="More hours"))
        unit_of_work.commit()

    with pytest.raises(AuthorizationError):
        service.operational_report(member.id or 0)

    report = service.operational_report(librarian.id or 0)

    assert report.active_users == 2
    assert report.catalog_titles == 1
    assert (report.available_copies, report.total_copies) == (1, 2)
    assert (report.active_loans, report.overdue_loans) == (1, 1)
    assert report.active_reservations == 1
    assert (report.outstanding_fines, report.outstanding_fine_amount) == (1, Decimal("12.34"))
    assert (report.pending_requests, report.new_feedback) == (1, 1)
