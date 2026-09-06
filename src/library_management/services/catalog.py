"""Catalog browsing and inventory-management use cases."""

from __future__ import annotations

from dataclasses import dataclass, replace

from library_management.domain import Book, BookCopy, BookCopyStatus, UserRole
from library_management.repositories import DuplicateRecordError, UnitOfWork
from library_management.services.accounts import UnitOfWorkFactory
from library_management.services.authorization import require_active_user, require_role
from library_management.services.errors import (
    CatalogConflictError,
    CatalogNotFoundError,
    InvalidCopyStatusTransitionError,
)

CATALOG_STAFF_ROLES = frozenset({UserRole.LIBRARIAN, UserRole.ADMINISTRATOR})
CATALOG_MANAGED_STATUSES = frozenset(
    {
        BookCopyStatus.AVAILABLE,
        BookCopyStatus.DAMAGED,
        BookCopyStatus.LOST,
        BookCopyStatus.WITHDRAWN,
    }
)


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    book: Book
    total_copies: int
    available_copies: int


class CatalogService:
    """Coordinate catalog reads and staff-controlled inventory changes."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def browse(self, actor_id: int, query: str | None = None) -> list[CatalogEntry]:
        with self._unit_of_work_factory() as unit_of_work:
            require_active_user(unit_of_work, actor_id)
            books = (
                unit_of_work.books.list_all() if query is None else unit_of_work.books.search(query)
            )
            return [self._entry(unit_of_work, book) for book in books]

    def get_book(self, actor_id: int, book_id: int) -> CatalogEntry:
        with self._unit_of_work_factory() as unit_of_work:
            require_active_user(unit_of_work, actor_id)
            book = self._get_book(unit_of_work, book_id)
            return self._entry(unit_of_work, book)

    def list_copies(self, actor_id: int, book_id: int) -> list[BookCopy]:
        with self._unit_of_work_factory() as unit_of_work:
            require_active_user(unit_of_work, actor_id)
            self._get_book(unit_of_work, book_id)
            return unit_of_work.book_copies.list_for_book(book_id)

    def add_book(
        self,
        actor_id: int,
        title: str,
        author: str,
        publication_year: int,
        *,
        isbn: str | None = None,
        category: str | None = None,
        description: str | None = None,
    ) -> Book:
        book = Book(
            title=title,
            author=author,
            publication_year=publication_year,
            isbn=isbn,
            category=category,
            description=description,
        )
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.lock_rows(users=(actor_id,))
            self._require_catalog_staff(unit_of_work, actor_id)
            try:
                saved = unit_of_work.books.add(book)
            except DuplicateRecordError as error:
                raise CatalogConflictError("That book or ISBN already exists.") from error
            unit_of_work.commit()
        return saved

    def update_book(
        self,
        actor_id: int,
        book_id: int,
        title: str,
        author: str,
        publication_year: int,
        *,
        isbn: str | None = None,
        category: str | None = None,
        description: str | None = None,
    ) -> Book:
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.lock_rows(users=(actor_id,), books=(book_id,))
            self._require_catalog_staff(unit_of_work, actor_id)
            existing = self._get_book(unit_of_work, book_id)
            updated = Book(
                id=existing.id,
                title=title,
                author=author,
                publication_year=publication_year,
                isbn=isbn,
                category=category,
                description=description,
                created_at=existing.created_at,
            )
            try:
                unit_of_work.books.update(updated)
            except DuplicateRecordError as error:
                raise CatalogConflictError("That book or ISBN already exists.") from error
            unit_of_work.commit()
        return updated

    def add_copy(self, actor_id: int, book_id: int, barcode: str) -> BookCopy:
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.lock_rows(users=(actor_id,), books=(book_id,))
            self._require_catalog_staff(unit_of_work, actor_id)
            self._get_book(unit_of_work, book_id)
            try:
                saved = unit_of_work.book_copies.add(BookCopy(book_id=book_id, barcode=barcode))
            except DuplicateRecordError as error:
                raise CatalogConflictError("That barcode already exists.") from error
            unit_of_work.commit()
        return saved

    def update_copy_status(
        self,
        actor_id: int,
        barcode: str,
        status: BookCopyStatus,
    ) -> BookCopy:
        with self._unit_of_work_factory() as unit_of_work:
            copy = unit_of_work.book_copies.get_by_barcode(barcode)
            if copy is None:
                raise CatalogNotFoundError(f"Book copy '{barcode.strip()}' was not found.")
            if copy.id is None:
                raise RuntimeError("A stored book copy is missing its identifier.")
            unit_of_work.lock_rows(users=(actor_id,), books=(copy.book_id,), book_copies=(copy.id,))
            self._require_catalog_staff(unit_of_work, actor_id)
            copy = unit_of_work.book_copies.get_by_id(copy.id)
            if copy is None or copy.id is None:
                raise CatalogNotFoundError(f"Book copy '{barcode.strip()}' was not found.")
            if status not in CATALOG_MANAGED_STATUSES:
                raise InvalidCopyStatusTransitionError(
                    "The on-loan status can only be changed by circulation workflows."
                )
            if copy.status is BookCopyStatus.ON_LOAN:
                raise InvalidCopyStatusTransitionError(
                    "An on-loan copy can only be changed by circulation workflows."
                )
            if copy.status is BookCopyStatus.WITHDRAWN and status is not BookCopyStatus.WITHDRAWN:
                raise InvalidCopyStatusTransitionError(
                    "A withdrawn copy cannot be restored through catalog management."
                )
            if copy.status is status:
                return copy
            unit_of_work.book_copies.update_status(copy.id, status)
            unit_of_work.commit()
        return replace(copy, status=status)

    @staticmethod
    def _get_book(unit_of_work: UnitOfWork, book_id: int) -> Book:
        book = unit_of_work.books.get_by_id(book_id)
        if book is None:
            raise CatalogNotFoundError(f"Book {book_id} was not found.")
        return book

    @staticmethod
    def _entry(unit_of_work: UnitOfWork, book: Book) -> CatalogEntry:
        if book.id is None:
            raise RuntimeError("A catalog book is missing its persistent identifier.")
        copies = unit_of_work.book_copies.list_for_book(book.id)
        return CatalogEntry(
            book=book,
            total_copies=len(copies),
            available_copies=sum(copy.status is BookCopyStatus.AVAILABLE for copy in copies),
        )

    @staticmethod
    def _require_catalog_staff(unit_of_work: UnitOfWork, actor_id: int) -> None:
        require_role(
            unit_of_work,
            actor_id,
            CATALOG_STAFF_ROLES,
            "Librarian or administrator permission is required.",
        )
