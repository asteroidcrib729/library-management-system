"""Transport-neutral keyset pagination values."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CatalogCursor:
    title_key: str
    identifier: int


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: tuple[T, ...]
    next_cursor: CatalogCursor | None
