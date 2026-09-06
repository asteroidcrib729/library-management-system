from pathlib import Path

import pytest

from library_management.database import Database


@pytest.fixture
def database(tmp_path: Path) -> Database:
    instance = Database(tmp_path / "library.db")
    instance.initialize()
    return instance
