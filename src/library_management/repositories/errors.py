"""Persistence-specific exceptions safe for application services to handle."""


class PersistenceError(Exception):
    """Base class for expected persistence failures."""


class DuplicateRecordError(PersistenceError):
    """Raised when a unique entity or identifier already exists."""


class RecordNotFoundError(PersistenceError):
    """Raised when an update targets a missing record."""
