from pathlib import Path

from library_management.config import Settings


def test_settings_build_application_paths(tmp_path: Path) -> None:
    settings = Settings(data_directory=tmp_path)

    assert settings.database_path == tmp_path / "library.db"
    assert settings.history_path == tmp_path / "cli-history"
    assert settings.backup_directory == tmp_path / "backups"


def test_prepare_creates_data_directory(tmp_path: Path) -> None:
    data_directory = tmp_path / "nested" / "data"

    Settings(data_directory=data_directory).prepare()

    assert data_directory.is_dir()
    assert (data_directory / "backups").is_dir()
