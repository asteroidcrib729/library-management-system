"""Domain-specific exceptions."""


class DomainError(Exception):
    """Base class for business-domain failures."""


class DomainValidationError(DomainError, ValueError):
    """Raised when an entity would be created in an invalid state."""
