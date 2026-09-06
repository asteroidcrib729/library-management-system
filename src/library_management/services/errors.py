"""Expected application-service failures suitable for presentation to users."""


class ApplicationError(Exception):
    """Base class for expected use-case failures."""


class AuthenticationError(ApplicationError):
    """Raised when supplied credentials cannot authenticate an active account."""


class AuthorizationError(ApplicationError):
    """Raised when an authenticated account cannot perform an operation."""


class UsernameUnavailableError(ApplicationError):
    """Raised when a requested username already exists."""


class BootstrapClosedError(ApplicationError):
    """Raised after initial administrator setup is no longer available."""


class LastAdministratorError(ApplicationError):
    """Raised when deactivation would leave no active administrator."""


class PasswordPolicyError(ApplicationError, ValueError):
    """Raised when a password does not satisfy the application policy."""


class CatalogError(ApplicationError):
    """Base class for expected catalog workflow failures."""


class CatalogNotFoundError(CatalogError):
    """Raised when a requested book or copy does not exist."""


class CatalogConflictError(CatalogError):
    """Raised when a book identity, ISBN, or barcode conflicts."""


class InvalidCopyStatusTransitionError(CatalogError):
    """Raised when catalog management cannot perform a copy status change."""


class CirculationError(ApplicationError):
    """Base class for expected reservation and loan failures."""


class CirculationNotFoundError(CirculationError):
    """Raised when a circulation record or related entity is missing."""


class ReservationConflictError(CirculationError):
    """Raised when a reservation violates current circulation state."""


class ReservationQueueError(CirculationError):
    """Raised when checkout would bypass reservation priority."""


class CopyUnavailableError(CirculationError):
    """Raised when a physical copy cannot be checked out or returned."""


class LoanLimitError(CirculationError):
    """Raised when an account has reached its active-loan limit."""


class RenewalNotAllowedError(CirculationError):
    """Raised when an active loan is not currently renewable."""


class FinancialError(ApplicationError):
    """Base class for expected fine and settlement failures."""


class FinancialNotFoundError(FinancialError):
    """Raised when a fine or related account does not exist."""


class FineSettlementError(FinancialError):
    """Raised when a fine cannot be paid or waived."""


class EngagementError(ApplicationError):
    """Base class for expected request and feedback failures."""


class EngagementNotFoundError(EngagementError):
    """Raised when a submission or related record does not exist."""


class SubmissionConflictError(EngagementError):
    """Raised when a duplicate submission is attempted."""


class InvalidSubmissionTransitionError(EngagementError):
    """Raised when a request or feedback transition is not allowed."""


class InsightsError(ApplicationError):
    """Base class for recommendation and reporting failures."""


class InvalidResultLimitError(InsightsError):
    """Raised when a requested result limit is outside policy bounds."""


class MaintenanceError(ApplicationError):
    """Base class for expected database maintenance failures."""


class BackupNotFoundError(MaintenanceError):
    """Raised when a managed backup filename does not exist."""


class BackupValidationError(MaintenanceError):
    """Raised when a database is unsafe or incompatible for backup restoration."""
