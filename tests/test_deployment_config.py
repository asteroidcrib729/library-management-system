import json
from pathlib import Path

from scripts.validate_deployment import REPOSITORY_ROOT, validate_repository


def test_committed_deployment_configuration_is_consistent() -> None:
    assert validate_repository() == []


def test_validator_rejects_database_secret_in_vercel_configuration(tmp_path: Path) -> None:
    _copy_contract_files(tmp_path)
    vercel_path = tmp_path / "web" / "vercel.json"
    vercel = json.loads(vercel_path.read_text(encoding="utf-8"))
    vercel["env"] = {"DATABASE_URL": "forbidden"}
    vercel_path.write_text(json.dumps(vercel), encoding="utf-8")

    assert any("DATABASE_URL" in error for error in validate_repository(tmp_path))


def test_validator_rejects_automatic_staging_deployment(tmp_path: Path) -> None:
    _copy_contract_files(tmp_path)
    workflow_path = tmp_path / ".github" / "workflows" / "deploy-staging.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    workflow_path.write_text(workflow.replace("workflow_dispatch:", "push:"), encoding="utf-8")

    assert any("manual" in error for error in validate_repository(tmp_path))


def _copy_contract_files(target: Path) -> None:
    paths = (
        Path("deploy/environment-contract.json"),
        Path("render.yaml"),
        Path("web/vercel.json"),
        Path(".github/workflows/deploy-staging.yml"),
        Path(".github/workflows/backup-staging.yml"),
    )
    for relative in paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            (REPOSITORY_ROOT / relative).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
