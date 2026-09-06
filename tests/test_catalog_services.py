from collections.abc import Callable
from functools import partial

import pytest

from library_management.database import Database
from library_management.domain import Book, BookCopyStatus, User, UserRole
from library_management.repositories import UnitOfWork
from library_management.repositories.sqlite import SqliteUnitOfWork
from library_management.services import (
    AuthorizationError,
    CatalogConflictError,
    CatalogNotFoundError,
    CatalogService,
    InvalidCopyStatusTransitionError,
)


def build_factory(database: Database) -> Callable[[], UnitOfWork]:
    return partial(SqliteUnitOfWork, database)


def add_user(database: Database, username: str, role: UserRole) -> User:
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


def add_default_book(service: CatalogService, staff_id: int) -> Book:
    return service.add_book(
        staff_id,
        "The Left Hand of Darkness",
        "Ursula K. Le Guin",
        1969,
        isbn="978-0-441-47812-5",
        category="Science Fiction",
    )


def test_member_can_browse_search_and_inspect_catalog(database: Database) -> None:
    service = CatalogService(build_factory(database))
    administrator = add_user(database, "admin", UserRole.ADMINISTRATOR)
    member = add_user(database, "reader.one", UserRole.MEMBER)
    book = add_default_book(service, administrator.id or 0)
    service.add_copy(administrator.id or 0, book.id or 0, "COPY-001")

    entries = service.browse(member.id or 0, "le guin")
    entry = service.get_book(member.id or 0, book.id or 0)
    copies = service.list_copies(member.id or 0, book.id or 0)

    assert entries == [entry]
    assert entry.book.isbn == "9780441478125"
    assert entry.total_copies == 1
    assert entry.available_copies == 1
    assert [copy.barcode for copy in copies] == ["COPY-001"]


def test_member_cannot_mutate_catalog(database: Database) -> None:
    service = CatalogService(build_factory(database))
    member = add_user(database, "reader.one", UserRole.MEMBER)

    with pytest.raises(AuthorizationError, match="Librarian or administrator"):
        service.add_book(member.id or 0, "Dune", "Frank Herbert", 1965)


@pytest.mark.parametrize("role", [UserRole.LIBRARIAN, UserRole.ADMINISTRATOR])
def test_catalog_staff_can_add_and_update_books(database: Database, role: UserRole) -> None:
    service = CatalogService(build_factory(database))
    staff = add_user(database, f"{role.value}.one", role)
    book = add_default_book(service, staff.id or 0)

    updated = service.update_book(
        staff.id or 0,
        book.id or 0,
        book.title,
        book.author,
        1970,
        isbn=book.isbn,
        category=book.category,
        description="Updated edition metadata",
    )

    assert updated.id == book.id
    assert updated.created_at == book.created_at
    assert updated.publication_year == 1970
    assert updated.description == "Updated edition metadata"


def test_duplicate_book_and_barcode_conflicts_are_safe(database: Database) -> None:
    service = CatalogService(build_factory(database))
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    book = add_default_book(service, librarian.id or 0)
    service.add_copy(librarian.id or 0, book.id or 0, "COPY-001")

    with pytest.raises(CatalogConflictError, match="book or ISBN"):
        add_default_book(service, librarian.id or 0)
    with pytest.raises(CatalogConflictError, match="barcode"):
        service.add_copy(librarian.id or 0, book.id or 0, "copy-001")


def test_copy_status_transitions_protect_circulation_state(database: Database) -> None:
    service = CatalogService(build_factory(database))
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    book = add_default_book(service, librarian.id or 0)
    copy = service.add_copy(librarian.id or 0, book.id or 0, "COPY-001")

    damaged = service.update_copy_status(librarian.id or 0, copy.barcode, BookCopyStatus.DAMAGED)
    withdrawn = service.update_copy_status(
        librarian.id or 0, copy.barcode, BookCopyStatus.WITHDRAWN
    )

    assert damaged.status is BookCopyStatus.DAMAGED
    assert withdrawn.status is BookCopyStatus.WITHDRAWN
    with pytest.raises(InvalidCopyStatusTransitionError, match="cannot be restored"):
        service.update_copy_status(librarian.id or 0, copy.barcode, BookCopyStatus.AVAILABLE)


def test_catalog_cannot_assign_or_override_on_loan_status(database: Database) -> None:
    service = CatalogService(build_factory(database))
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)
    book = add_default_book(service, librarian.id or 0)
    copy = service.add_copy(librarian.id or 0, book.id or 0, "COPY-001")

    with pytest.raises(InvalidCopyStatusTransitionError, match="circulation"):
        service.update_copy_status(librarian.id or 0, copy.barcode, BookCopyStatus.ON_LOAN)

    with SqliteUnitOfWork(database) as unit_of_work:
        unit_of_work.book_copies.update_status(copy.id or 0, BookCopyStatus.ON_LOAN)
        unit_of_work.commit()

    with pytest.raises(InvalidCopyStatusTransitionError, match="circulation"):
        service.update_copy_status(librarian.id or 0, copy.barcode, BookCopyStatus.DAMAGED)


def test_missing_book_and_copy_have_catalog_errors(database: Database) -> None:
    service = CatalogService(build_factory(database))
    librarian = add_user(database, "librarian.one", UserRole.LIBRARIAN)

    with pytest.raises(CatalogNotFoundError, match="Book 999"):
        service.get_book(librarian.id or 0, 999)
    with pytest.raises(CatalogNotFoundError, match="MISSING-001"):
        service.update_copy_status(librarian.id or 0, "MISSING-001", BookCopyStatus.DAMAGED)


def test_deactivated_user_cannot_browse(database: Database) -> None:
    service = CatalogService(build_factory(database))
    member = add_user(database, "reader.one", UserRole.MEMBER)
    with SqliteUnitOfWork(database) as unit_of_work:
        unit_of_work.users.deactivate(member.id or 0)
        unit_of_work.commit()

    with pytest.raises(AuthorizationError, match="active account"):
        service.browse(member.id or 0)
