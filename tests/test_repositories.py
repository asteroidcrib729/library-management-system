import pytest

from library_management.database import Database
from library_management.domain import Book, BookCopy, BookCopyStatus, User
from library_management.repositories import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.sqlite import SqliteUnitOfWork


def new_user(username: str = "reader.one") -> User:
    return User(
        display_name="Reader One",
        username=username,
        password_hash="$argon2id$test-hash",
    )


def new_book() -> Book:
    return Book(
        title="The Left Hand of Darkness",
        author="Ursula K. Le Guin",
        publication_year=1969,
        isbn="9780441478125",
    )


def test_committed_user_is_available_in_a_later_unit_of_work(database: Database) -> None:
    with SqliteUnitOfWork(database) as unit_of_work:
        saved = unit_of_work.users.add(new_user())
        unit_of_work.commit()

    assert saved.id is not None
    with SqliteUnitOfWork(database) as unit_of_work:
        loaded = unit_of_work.users.get_by_username("READER.ONE")

    assert loaded == saved


def test_uncommitted_changes_are_rolled_back(database: Database) -> None:
    with SqliteUnitOfWork(database) as unit_of_work:
        unit_of_work.users.add(new_user())

    with SqliteUnitOfWork(database) as unit_of_work:
        loaded = unit_of_work.users.get_by_username("reader.one")

    assert loaded is None


def test_duplicate_username_is_translated_to_persistence_error(database: Database) -> None:
    with SqliteUnitOfWork(database) as unit_of_work:
        unit_of_work.users.add(new_user())
        unit_of_work.commit()

    with (
        pytest.raises(DuplicateRecordError, match="already exists"),
        SqliteUnitOfWork(database) as unit_of_work,
    ):
        unit_of_work.users.add(new_user("READER.ONE"))


def test_book_search_and_copy_lifecycle(database: Database) -> None:
    with SqliteUnitOfWork(database) as unit_of_work:
        saved_book = unit_of_work.books.add(new_book())
        assert saved_book.id is not None
        saved_copy = unit_of_work.book_copies.add(
            BookCopy(book_id=saved_book.id, barcode="copy-001")
        )
        unit_of_work.commit()

    assert saved_copy.id is not None
    with SqliteUnitOfWork(database) as unit_of_work:
        search_results = unit_of_work.books.search("le guin")
        loaded_copy = unit_of_work.book_copies.get_by_barcode("COPY-001")
        unit_of_work.book_copies.update_status(saved_copy.id, BookCopyStatus.DAMAGED)
        unit_of_work.commit()

    assert search_results == [saved_book]
    assert loaded_copy == saved_copy

    with SqliteUnitOfWork(database) as unit_of_work:
        updated_copy = unit_of_work.book_copies.get_by_id(saved_copy.id)

    assert updated_copy is not None
    assert updated_copy.status is BookCopyStatus.DAMAGED


def test_duplicate_book_identity_is_rejected(database: Database) -> None:
    with SqliteUnitOfWork(database) as unit_of_work:
        unit_of_work.books.add(new_book())
        unit_of_work.commit()

    duplicate = Book(
        title="the left hand of darkness",
        author="URSULA K. LE GUIN",
        publication_year=1969,
    )
    with pytest.raises(DuplicateRecordError), SqliteUnitOfWork(database) as unit_of_work:
        unit_of_work.books.add(duplicate)


def test_repository_access_requires_active_unit_of_work(database: Database) -> None:
    unit_of_work = SqliteUnitOfWork(database)

    with pytest.raises(RuntimeError, match="must be entered"):
        _ = unit_of_work.users


def test_book_copy_requires_an_existing_book(database: Database) -> None:
    with (
        pytest.raises(RecordNotFoundError, match="Book 999"),
        SqliteUnitOfWork(database) as unit_of_work,
    ):
        unit_of_work.book_copies.add(BookCopy(book_id=999, barcode="ORPHAN-001"))
