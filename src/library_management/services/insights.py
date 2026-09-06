"""Explainable catalog recommendations and operational reporting."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from library_management.domain import Book, BookCopyStatus, UserRole
from library_management.repositories import UnitOfWork
from library_management.services.accounts import UnitOfWorkFactory
from library_management.services.authorization import require_active_user, require_role
from library_management.services.errors import InvalidResultLimitError

Clock = Callable[[], datetime]
REPORTING_STAFF_ROLES = frozenset({UserRole.LIBRARIAN, UserRole.ADMINISTRATOR})


def system_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class RecommendationPolicy:
    default_limit: int = 5
    maximum_limit: int = 20
    category_weight: int = 100
    author_weight: int = 50
    popularity_weight: int = 2
    availability_weight: int = 1
    popularity_cap: int = 20
    availability_cap: int = 10

    def __post_init__(self) -> None:
        if self.default_limit <= 0 or self.maximum_limit < self.default_limit:
            raise ValueError("Recommendation limits must be positive and ordered.")
        weights = (
            self.category_weight,
            self.author_weight,
            self.popularity_weight,
            self.availability_weight,
        )
        if any(weight <= 0 for weight in weights):
            raise ValueError("Recommendation weights must be positive.")
        if self.popularity_cap <= 0 or self.availability_cap <= 0:
            raise ValueError("Recommendation signal caps must be positive.")


@dataclass(frozen=True, slots=True)
class RecommendationView:
    book: Book
    score: int
    reason: str
    available_copies: int
    historical_checkouts: int


@dataclass(frozen=True, slots=True)
class PopularBookView:
    book: Book
    historical_checkouts: int
    available_copies: int


@dataclass(frozen=True, slots=True)
class OperationalReport:
    generated_at: datetime
    active_users: int
    catalog_titles: int
    total_copies: int
    available_copies: int
    active_loans: int
    overdue_loans: int
    active_reservations: int
    outstanding_fines: int
    outstanding_fine_amount: Decimal
    pending_requests: int
    new_feedback: int
    popular_books: tuple[PopularBookView, ...]


class InsightsService:
    """Build read-only recommendations and staff operations reports."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        policy: RecommendationPolicy | None = None,
        clock: Clock = system_clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._policy = policy or RecommendationPolicy()
        self._clock = clock

    def recommend(self, actor_id: int, limit: int | None = None) -> list[RecommendationView]:
        selected_limit = self._validate_limit(limit)
        with self._unit_of_work_factory() as unit_of_work:
            actor = require_active_user(unit_of_work, actor_id)
            if actor.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            borrowed_book_ids: set[int] = set()
            categories: Counter[str] = Counter()
            authors: Counter[str] = Counter()
            for loan in unit_of_work.loans.list_for_user(actor.id):
                copy = unit_of_work.book_copies.get_by_id(loan.book_copy_id)
                if copy is None:
                    continue
                book = unit_of_work.books.get_by_id(copy.book_id)
                if book is None or book.id is None:
                    continue
                borrowed_book_ids.add(book.id)
                authors[book.author.casefold()] += 1
                if book.category:
                    categories[book.category.casefold()] += 1

            loan_counts = unit_of_work.reporting.loan_counts_by_book()
            ranked: list[RecommendationView] = []
            for book in unit_of_work.books.list_all():
                if book.id is None or book.id in borrowed_book_ids:
                    continue
                copies = unit_of_work.book_copies.list_for_book(book.id)
                available = sum(copy.status is BookCopyStatus.AVAILABLE for copy in copies)
                if available == 0:
                    continue
                category_affinity = categories[book.category.casefold()] if book.category else 0
                author_affinity = authors[book.author.casefold()]
                historical_checkouts = loan_counts.get(book.id, 0)
                score = (
                    category_affinity * self._policy.category_weight
                    + author_affinity * self._policy.author_weight
                    + min(historical_checkouts, self._policy.popularity_cap)
                    * self._policy.popularity_weight
                    + min(available, self._policy.availability_cap)
                    * self._policy.availability_weight
                )
                reason = self._recommendation_reason(
                    book, category_affinity, author_affinity, historical_checkouts
                )
                ranked.append(
                    RecommendationView(book, score, reason, available, historical_checkouts)
                )

            ranked.sort(key=self._recommendation_sort_key)
            return ranked[:selected_limit]

    def popular(self, actor_id: int, limit: int | None = None) -> list[PopularBookView]:
        selected_limit = self._validate_limit(limit)
        with self._unit_of_work_factory() as unit_of_work:
            require_active_user(unit_of_work, actor_id)
            return self._popular_books(unit_of_work, selected_limit)

    def operational_report(self, actor_id: int) -> OperationalReport:
        now = self._now()
        with self._unit_of_work_factory() as unit_of_work:
            require_role(
                unit_of_work,
                actor_id,
                REPORTING_STAFF_ROLES,
                "Librarian or administrator permission is required.",
            )
            total_copies, available_copies = unit_of_work.reporting.count_copies()
            outstanding_count, outstanding_amount = unit_of_work.reporting.outstanding_fines()
            return OperationalReport(
                generated_at=now,
                active_users=unit_of_work.reporting.count_active_users(),
                catalog_titles=unit_of_work.reporting.count_titles(),
                total_copies=total_copies,
                available_copies=available_copies,
                active_loans=unit_of_work.reporting.count_active_loans(),
                overdue_loans=unit_of_work.reporting.count_overdue_loans(now),
                active_reservations=unit_of_work.reporting.count_active_reservations(),
                outstanding_fines=outstanding_count,
                outstanding_fine_amount=outstanding_amount,
                pending_requests=unit_of_work.reporting.count_pending_requests(),
                new_feedback=unit_of_work.reporting.count_new_feedback(),
                popular_books=tuple(self._popular_books(unit_of_work, 5)),
            )

    def _popular_books(self, unit_of_work: UnitOfWork, limit: int) -> list[PopularBookView]:
        loan_counts = unit_of_work.reporting.loan_counts_by_book()
        ranked: list[PopularBookView] = []
        for book in unit_of_work.books.list_all():
            if book.id is None:
                continue
            available = sum(
                copy.status is BookCopyStatus.AVAILABLE
                for copy in unit_of_work.book_copies.list_for_book(book.id)
            )
            if available:
                ranked.append(PopularBookView(book, loan_counts.get(book.id, 0), available))
        ranked.sort(key=self._popular_sort_key)
        return ranked[:limit]

    @staticmethod
    def _recommendation_sort_key(item: RecommendationView) -> tuple[int, str, int]:
        return -item.score, item.book.title.casefold(), item.book.id or 0

    @staticmethod
    def _popular_sort_key(item: PopularBookView) -> tuple[int, int, str, int]:
        return (
            -item.historical_checkouts,
            -item.available_copies,
            item.book.title.casefold(),
            item.book.id or 0,
        )

    def _validate_limit(self, limit: int | None) -> int:
        selected = self._policy.default_limit if limit is None else limit
        if not 1 <= selected <= self._policy.maximum_limit:
            raise InvalidResultLimitError(
                f"Result limit must be between 1 and {self._policy.maximum_limit}."
            )
        return selected

    @staticmethod
    def _recommendation_reason(
        book: Book,
        category_affinity: int,
        author_affinity: int,
        historical_checkouts: int,
    ) -> str:
        if category_affinity and book.category:
            return f"Matches your interest in {book.category}."
        if author_affinity:
            return f"You have borrowed another book by {book.author}."
        if historical_checkouts:
            return f"Popular with {historical_checkouts} historical checkout(s)."
        return "Available for a new catalog discovery."

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Insights clock must return a timezone-aware timestamp.")
        return value.astimezone(UTC)
