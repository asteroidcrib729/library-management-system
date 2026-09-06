"""Validate committed deployment contracts without contacting a provider."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPOSITORY_ROOT / "deploy" / "environment-contract.json"
RENDER_PATH = REPOSITORY_ROOT / "render.yaml"
VERCEL_PATH = REPOSITORY_ROOT / "web" / "vercel.json"
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "deploy-staging.yml"
BACKUP_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "backup-staging.yml"


def validate_repository(root: Path = REPOSITORY_ROOT) -> list[str]:
    """Return actionable validation failures; an empty result is success."""

    errors: list[str] = []
    contract_path = root / CONTRACT_PATH.relative_to(REPOSITORY_ROOT)
    render_path = root / RENDER_PATH.relative_to(REPOSITORY_ROOT)
    vercel_path = root / VERCEL_PATH.relative_to(REPOSITORY_ROOT)
    workflow_path = root / WORKFLOW_PATH.relative_to(REPOSITORY_ROOT)
    backup_workflow_path = root / BACKUP_WORKFLOW_PATH.relative_to(REPOSITORY_ROOT)
    for path in (contract_path, render_path, vercel_path, workflow_path, backup_workflow_path):
        if not path.is_file():
            errors.append(f"Missing deployment file: {path.relative_to(root)}")
    if errors:
        return errors

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        vercel = json.loads(vercel_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return [f"Invalid deployment JSON: {error}"]

    render = render_path.read_text(encoding="utf-8")
    workflow = workflow_path.read_text(encoding="utf-8")
    backup_workflow = backup_workflow_path.read_text(encoding="utf-8")
    _validate_render(render, contract, errors)
    _validate_vercel(vercel, contract, errors)
    _validate_workflow(workflow, contract, errors)
    _validate_backup_workflow(backup_workflow, contract, errors)
    return errors


def _validate_render(render: str, contract: dict[str, object], errors: list[str]) -> None:
    required_fragments = (
        "$schema=https://render.com/schema/render.yaml.json",
        "runtime: python",
        "autoDeployTrigger: off",
        "healthCheckPath: /health/live",
        "--host 0.0.0.0 --port $PORT",
        "plan: free",
    )
    for fragment in required_fragments:
        if fragment not in render:
            errors.append(f"render.yaml must contain {fragment!r}")
    if "preDeployCommand:" in render:
        errors.append("Render must not own database migration execution.")
    start_line = next((line for line in render.splitlines() if "startCommand:" in line), "")
    if any(word in start_line.lower() for word in ("migration", "migrate", "supabase")):
        errors.append("Render startCommand must only start the API.")
    declared = set(re.findall(r"^\s+- key: ([A-Z0-9_]+)\s*$", render, re.MULTILINE))
    expected = set(_string_list(contract, "render_runtime", errors))
    if declared != expected:
        errors.append(
            "render.yaml environment keys differ from the contract: "
            f"missing={sorted(expected - declared)}, extra={sorted(declared - expected)}"
        )
    if not re.search(r"- key: DATABASE_URL\s+sync: false", render):
        errors.append("DATABASE_URL must be an unsynchronized Render secret.")


def _validate_vercel(
    vercel: dict[str, object], contract: dict[str, object], errors: list[str]
) -> None:
    if vercel.get("framework") != "nextjs":
        errors.append("web/vercel.json must explicitly select Next.js.")
    if vercel.get("installCommand") != "npm ci":
        errors.append("Vercel must use the committed npm lockfile via npm ci.")
    serialized = json.dumps(vercel, sort_keys=True)
    for name in _string_list(contract, "forbidden_in_browser", errors):
        if name in serialized:
            errors.append(f"Browser deployment configuration contains forbidden name {name}.")


def _validate_workflow(workflow: str, contract: dict[str, object], errors: list[str]) -> None:
    if "workflow_dispatch:" not in workflow or "environment: staging" not in workflow:
        errors.append("Staging deployment must be manual and environment-protected.")
    if re.search(r"^\s+(push|pull_request):", workflow, re.MULTILINE):
        errors.append("Staging deployment must not run automatically on push or pull request.")
    referenced = set(re.findall(r"secrets\.([A-Z0-9_]+)", workflow))
    expected = set(_string_list(contract, "github_staging_secrets", errors))
    if referenced != expected:
        errors.append(
            "Workflow secret references differ from the contract: "
            f"missing={sorted(expected - referenced)}, extra={sorted(referenced - expected)}"
        )
    variables = set(re.findall(r"vars\.([A-Z0-9_]+)", workflow))
    expected_variables = set(_string_list(contract, "github_staging_variables", errors))
    if variables != expected_variables:
        errors.append(
            "Workflow variable references differ from the contract: "
            f"missing={sorted(expected_variables - variables)}, "
            f"extra={sorted(variables - expected_variables)}"
        )
    if "ref=${DEPLOY_SHA}" not in workflow:
        errors.append("Render deployment must identify the exact checked-out commit.")


def _validate_backup_workflow(
    workflow: str, contract: dict[str, object], errors: list[str]
) -> None:
    if "workflow_dispatch:" not in workflow or "environment: staging" not in workflow:
        errors.append("Staging backup must be manual and environment-protected.")
    if re.search(r"^\s+(push|pull_request|schedule):", workflow, re.MULTILINE):
        errors.append("Free-tier backup must not become an automatic keep-awake workflow.")
    referenced = set(re.findall(r"secrets\.([A-Z0-9_]+)", workflow))
    expected = set(_string_list(contract, "github_backup_secrets", errors))
    if referenced != expected:
        errors.append(
            "Backup secret references differ from the contract: "
            f"missing={sorted(expected - referenced)}, extra={sorted(referenced - expected)}"
        )
    variables = set(re.findall(r"vars\.([A-Z0-9_]+)", workflow))
    expected_variables = set(_string_list(contract, "github_backup_variables", errors))
    if variables != expected_variables:
        errors.append(
            "Backup variable references differ from the contract: "
            f"missing={sorted(expected_variables - variables)}, "
            f"extra={sorted(variables - expected_variables)}"
        )
    for fragment in (
        "age-v1.3.2",
        '-r "$BACKUP_AGE_RECIPIENT"',
        "verify-backup",
        "actions/upload-artifact@v7",
    ):
        if fragment not in workflow:
            errors.append(f"Staging backup workflow must contain {fragment!r}.")


def _string_list(contract: dict[str, object], key: str, errors: list[str]) -> list[str]:
    value = contract.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"Environment contract field {key!r} must be a string list.")
        return []
    return value


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    errors = validate_repository()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Deployment configuration is internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
