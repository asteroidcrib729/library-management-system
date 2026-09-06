import json
from pathlib import Path

import pytest

from scripts.classify_changes import classify_paths, main


def test_frontend_change_selects_only_frontend() -> None:
    assert classify_paths(["web/src/app/page.tsx"]) == {
        "backend": False,
        "database": False,
        "contract": False,
        "frontend": True,
        "docs": False,
    }


def test_contract_change_fans_out_to_producer_and_consumer() -> None:
    selection = classify_paths(["contracts/openapi.json"])
    assert selection["backend"] is True
    assert selection["contract"] is True
    assert selection["frontend"] is True
    assert selection["database"] is False


def test_database_change_also_checks_backend() -> None:
    selection = classify_paths(["supabase/config.toml"])
    assert selection["database"] is True
    assert selection["backend"] is True


def test_docs_only_change_does_not_start_code_checks() -> None:
    assert classify_paths(["README.md", "development-plans/development-plan-12.md"]) == {
        "backend": False,
        "database": False,
        "contract": False,
        "frontend": False,
        "docs": True,
    }


def test_deployment_and_unknown_changes_fail_open() -> None:
    assert all(classify_paths([".github/workflows/ci.yml"]).values())
    assert all(classify_paths(["render.yaml"]).values())
    assert all(classify_paths(["web/vercel.json"]).values())
    assert all(classify_paths(["deploy/environment-contract.json"]).values())
    assert all(classify_paths(["an-unclassified-file.txt"]).values())


def test_cli_writes_github_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "github-output.txt"

    assert main(["--github-output", str(output), "web/package.json"]) == 0

    values = dict(line.split("=", maxsplit=1) for line in output.read_text().splitlines())
    assert values["frontend"] == "true"
    assert values["backend"] == "false"
    printed = json.loads(capsys.readouterr().out)
    assert printed["frontend"] is True
