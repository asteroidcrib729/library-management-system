"""PostgreSQL catalog and physical-copy repositories."""

from __future__ import annotations

from dataclasses import replace

import psycopg
from psycopg import Connection

from library_management.domain import Book, BookCopy, BookCopyStatus
from library_management.postgres.database import Row
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.pagination import CatalogCursor, Page
from library_management.repositories.postgres.common import as_datetime, returned_row

MAX_PAGE_SIZE = 100


class PostgresBookRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, book: Book) -> Book:
        if book.id is not None:
            raise ValueError("A new book cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO books(isbn, title, author, publication_year, category,
                                      description, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (
                        book.isbn,
                        book.title,
                        book.author,
                        book.publication_year,
                        book.category,
                        book.description,
                        book.created_at,
                    ),
                ),
                "book identifier",
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError("The book or ISBN already exists.") from error
        return replace(book, id=int(row["id"]))

    def get_by_id(self, book_id: int) -> Book | None:
        row = self._connection.execute("SELECT * FROM books WHERE id = %s", (book_id,)).fetchone()
        return self._map(row) if row else None

    def update(self, book: Book) -> None:
        if book.id is None:
            raise ValueError("An updated book must have an identifier.")
        try:
            cursor = self._connection.execute(
                """
                UPDATE books SET isbn=%s, title=%s, author=%s, publication_year=%s,
                                 category=%s, description=%s
                WHERE id=%s
                """,
                (
                    book.isbn,
                    book.title,
                    book.author,
                    book.publication_year,
                    book.category,
                    book.description,
                    book.id,
                ),
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError("The book or ISBN already exists.") from error
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Book {book.id} was not found.")

    def list_all(self) -> list[Book]:
        rows = self._connection.execute(
            "SELECT * FROM books ORDER BY lower(title), lower(author), id"
        ).fetchall()
        return [self._map(row) for row in rows]

    def search(self, query: str) -> list[Book]:
        cleaned = query.strip()
        if not cleaned:
            return []
        escaped = cleaned.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        rows = self._connection.execute(
            """
            SELECT * FROM books
            WHERE title ILIKE %s ESCAPE '\\' OR author ILIKE %s ESCAPE '\\'
               OR isbn ILIKE %s ESCAPE '\\'
            ORDER BY lower(title), lower(author), id
            """,
            (pattern, pattern, pattern),
        ).fetchall()
        return [self._map(row) for row in rows]

    def page(
        self,
        *,
        limit: int = 25,
        after: CatalogCursor | None = None,
    ) -> Page[Book]:
        return self._page(None, limit, after)

    def search_page(
        self,
        query: str,
        *,
        limit: int = 25,
        after: CatalogCursor | None = None,
    ) -> Page[Book]:
        cleaned = query.strip()
        if not cleaned:
            return Page((), None)
        escaped = cleaned.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return self._page(f"%{escaped}%", limit, after)

    def _page(
        self,
        pattern: str | None,
        limit: int,
        after: CatalogCursor | None,
    ) -> Page[Book]:
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"Page size must be between 1 and {MAX_PAGE_SIZE}.")
        title_key = after.title_key if after else ""
        identifier = after.identifier if after else 0
        if pattern is None:
            rows = self._connection.execute(
                """
                SELECT *, lower(title) AS page_title_key FROM books
                WHERE (lower(title), id) > (%s, %s)
                ORDER BY lower(title), id LIMIT %s
                """,
                (title_key, identifier, limit + 1),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT *, lower(title) AS page_title_key FROM books
                WHERE (title ILIKE %s ESCAPE '\\' OR author ILIKE %s ESCAPE '\\'
                       OR isbn ILIKE %s ESCAPE '\\')
                  AND (lower(title), id) > (%s, %s)
                ORDER BY lower(title), id LIMIT %s
                """,
                (pattern, pattern, pattern, title_key, identifier, limit + 1),
            ).fetchall()
        items = tuple(self._map(row) for row in rows[:limit])
        next_cursor = None
        if len(rows) > limit and items:
            last = items[-1]
            if last.id is None:
                raise RuntimeError("Stored book is missing its identifier.")
            next_cursor = CatalogCursor(str(rows[limit - 1]["page_title_key"]), last.id)
        return Page(items, next_cursor)

    @staticmethod
    def _map(row: Row) -> Book:
        return Book(
            id=int(row["id"]),
            isbn=str(row["isbn"]) if row["isbn"] is not None else None,
            title=str(row["title"]),
            author=str(row["author"]),
            publication_year=int(row["publication_year"]),
            category=str(row["category"]) if row["category"] is not None else None,
            description=str(row["description"]) if row["description"] is not None else None,
            created_at=as_datetime(row["created_at"]),
        )


class PostgresBookCopyRepository:
    def __init__(self, connection: Connection[Row]) -> None:
        self._connection = connection

    def add(self, copy: BookCopy) -> BookCopy:
        if copy.id is not None:
            raise ValueError("A new book copy cannot already have an identifier.")
        try:
            row = returned_row(
                self._connection.execute(
                    """
                    INSERT INTO book_copies(book_id, barcode, status, created_at)
                    VALUES (%s, %s, %s, %s) RETURNING id
                    """,
                    (copy.book_id, copy.barcode, copy.status.value, copy.created_at),
                ),
                "book-copy identifier",
            )
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateRecordError(f"Barcode '{copy.barcode}' already exists.") from error
        except psycopg.errors.ForeignKeyViolation as error:
            raise RecordNotFoundError(f"Book {copy.book_id} was not found.") from error
        return replace(copy, id=int(row["id"]))

    def get_by_id(self, copy_id: int) -> BookCopy | None:
        row = self._connection.execute(
            "SELECT * FROM book_copies WHERE id = %s", (copy_id,)
        ).fetchone()
        return self._map(row) if row else None

    def get_by_barcode(self, barcode: str) -> BookCopy | None:
        row = self._connection.execute(
            "SELECT * FROM book_copies WHERE lower(barcode) = lower(%s)",
            (barcode.strip(),),
        ).fetchone()
        return self._map(row) if row else None

    def list_for_book(self, book_id: int) -> list[BookCopy]:
        rows = self._connection.execute(
            "SELECT * FROM book_copies WHERE book_id = %s ORDER BY id", (book_id,)
        ).fetchall()
        return [self._map(row) for row in rows]

    def update_status(self, copy_id: int, status: BookCopyStatus) -> None:
        cursor = self._connection.execute(
            "UPDATE book_copies SET status = %s WHERE id = %s",
            (status.value, copy_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Book copy {copy_id} was not found.")

    @staticmethod
    def _map(row: Row) -> BookCopy:
        return BookCopy(
            id=int(row["id"]),
            book_id=int(row["book_id"]),
            barcode=str(row["barcode"]),
            status=BookCopyStatus(str(row["status"])),
            created_at=as_datetime(row["created_at"]),
        )
