"""Safe failures raised by migration and recovery operations."""


class DataMigrationError(Exception):
    """Base class for expected migration failures."""


class SnapshotValidationError(DataMigrationError):
    """The SQLite source is missing, incompatible, corrupt, or inconsistent."""


class TargetNotEmptyError(DataMigrationError):
    """The PostgreSQL target contains application data and cannot be imported into."""


class ReconciliationError(DataMigrationError):
    """Source and target counts, metrics, or canonical row digests differ."""


class LogicalRecoveryError(DataMigrationError):
    """A logical backup or guarded restore operation failed."""
