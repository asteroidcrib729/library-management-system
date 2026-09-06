"""SQLite book and physical-copy repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from library_management.domain import Book, BookCopy, BookCopyStatus
from library_management.repositories.errors import DuplicateRecordError, RecordNotFoundError
from library_management.repositories.sqlite.mapping import (
    from_database_datetime,
    to_database_datetime,
)


class SqliteBookRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, book: Book) -> Book:
        if book.id is not None:
            raise ValueError("A new book cannot already have an identifier.")
        try:
            cursor = self._connection.execute(
                """
                INSERT INTO books(
                    isbn, title, author, publication_year, category, description, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    book.isbn,
                    book.title,
                    book.author,
                    book.publication_year,
                    book.category,
                    book.description,
                    to_database_datetime(book.created_at),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError("The book or ISBN already exists.") from error
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the new book.")
        return replace(book, id=cursor.lastrowid)

    def get_by_id(self, book_id: int) -> Book | None:
        row = self._connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._map(row) if row is not None else None

    def update(self, book: Book) -> None:
        if book.id is None:
            raise ValueError("An updated book must have an identifier.")
        try:
            cursor = self._connection.execute(
                """
                UPDATE books
                SET isbn = ?, title = ?, author = ?, publication_year = ?,
                    category = ?, description = ?
                WHERE id = ?
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
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError("The book or ISBN already exists.") from error
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Book {book.id} was not found.")

    def list_all(self) -> list[Book]:
        rows = self._connection.execute(
            "SELECT * FROM books ORDER BY title COLLATE NOCASE, author COLLATE NOCASE, id"
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
            WHERE title LIKE ? ESCAPE '\\' COLLATE NOCASE
               OR author LIKE ? ESCAPE '\\' COLLATE NOCASE
               OR isbn LIKE ? ESCAPE '\\' COLLATE NOCASE
            ORDER BY title COLLATE NOCASE, author COLLATE NOCASE, id
            """,
            (pattern, pattern, pattern),
        ).fetchall()
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: sqlite3.Row) -> Book:
        return Book(
            id=int(row["id"]),
            isbn=str(row["isbn"]) if row["isbn"] is not None else None,
            title=str(row["title"]),
            author=str(row["author"]),
            publication_year=int(row["publication_year"]),
            category=str(row["category"]) if row["category"] is not None else None,
            description=str(row["description"]) if row["description"] is not None else None,
            created_at=from_database_datetime(str(row["created_at"])),
        )


class SqliteBookCopyRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, copy: BookCopy) -> BookCopy:
        if copy.id is not None:
            raise ValueError("A new book copy cannot already have an identifier.")
        book_exists = self._connection.execute(
            "SELECT 1 FROM books WHERE id = ?", (copy.book_id,)
        ).fetchone()
        if book_exists is None:
            raise RecordNotFoundError(f"Book {copy.book_id} was not found.")
        try:
            cursor = self._connection.execute(
                """
                INSERT INTO book_copies(book_id, barcode, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    copy.book_id,
                    copy.barcode,
                    copy.status.value,
                    to_database_datetime(copy.created_at),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateRecordError(f"Barcode '{copy.barcode}' already exists.") from error
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the new book copy.")
        return replace(copy, id=cursor.lastrowid)

    def get_by_id(self, copy_id: int) -> BookCopy | None:
        row = self._connection.execute(
            "SELECT * FROM book_copies WHERE id = ?", (copy_id,)
        ).fetchone()
        return self._map(row) if row is not None else None

    def get_by_barcode(self, barcode: str) -> BookCopy | None:
        row = self._connection.execute(
            "SELECT * FROM book_copies WHERE barcode = ? COLLATE NOCASE",
            (barcode.strip(),),
        ).fetchone()
        return self._map(row) if row is not None else None

    def list_for_book(self, book_id: int) -> list[BookCopy]:
        rows = self._connection.execute(
            "SELECT * FROM book_copies WHERE book_id = ? ORDER BY id",
            (book_id,),
        ).fetchall()
        return [self._map(row) for row in rows]

    def update_status(self, copy_id: int, status: BookCopyStatus) -> None:
        cursor = self._connection.execute(
            "UPDATE book_copies SET status = ? WHERE id = ?",
            (status.value, copy_id),
        )
        if cursor.rowcount == 0:
            raise RecordNotFoundError(f"Book copy {copy_id} was not found.")

    @staticmethod
    def _map(row: sqlite3.Row) -> BookCopy:
        return BookCopy(
            id=int(row["id"]),
            book_id=int(row["book_id"]),
            barcode=str(row["barcode"]),
            status=BookCopyStatus(str(row["status"])),
            created_at=from_database_datetime(str(row["created_at"])),
        )
