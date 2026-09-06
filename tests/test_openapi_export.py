from pathlib import Path

from library_management.api.openapi import render_contract
from scripts.export_openapi import main


def test_openapi_export_and_check_are_deterministic(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    assert main(["--output", str(output)]) == 0
    first = output.read_text(encoding="utf-8")
    assert first == render_contract()
    assert main(["--check", "--output", str(output)]) == 0


def test_openapi_check_detects_stale_contract(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    output.write_text("{}\n", encoding="utf-8")

    assert main(["--check", "--output", str(output)]) == 1
