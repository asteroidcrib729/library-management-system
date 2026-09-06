"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime paths and application-level settings."""

    data_directory: Path

    @classmethod
    def from_environment(cls) -> Settings:
        """Build settings, allowing the data directory to be overridden."""
        configured_directory = os.environ.get("LMS_DATA_DIRECTORY")
        data_directory = (
            Path(configured_directory).expanduser() if configured_directory else Path.cwd() / ".lms"
        )
        return cls(data_directory=data_directory)

    @property
    def database_path(self) -> Path:
        return self.data_directory / "library.db"

    @property
    def history_path(self) -> Path:
        return self.data_directory / "cli-history"

    @property
    def backup_directory(self) -> Path:
        return self.data_directory / "backups"

    def prepare(self) -> None:
        """Create directories needed by the local application."""
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
