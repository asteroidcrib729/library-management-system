"""Classify repository paths for component-aware continuous integration."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Literal, TypedDict


class Selection(TypedDict):
    backend: bool
    database: bool
    contract: bool
    frontend: bool
    docs: bool


Component = Literal["backend", "database", "contract", "frontend", "docs"]
COMPONENTS: tuple[Component, ...] = (
    "backend",
    "database",
    "contract",
    "frontend",
    "docs",
)


def _empty_selection() -> Selection:
    return {
        "backend": False,
        "database": False,
        "contract": False,
        "frontend": False,
        "docs": False,
    }


def _all_components() -> Selection:
    return {
        "backend": True,
        "database": True,
        "contract": True,
        "frontend": True,
        "docs": True,
    }


def _normalize_path(raw_path: str) -> str:
    path = raw_path.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path


def classify_paths(paths: Iterable[str]) -> Selection:
    """Return the checks required for *paths*, failing open for unknown files."""
    selection = _empty_selection()

    for raw_path in paths:
        path = _normalize_path(raw_path)
        if not path:
            continue

        if path.startswith((".github/", "deploy/")) or path in {
            "render.yaml",
            "vercel.json",
            "web/vercel.json",
        }:
            return _all_components()

        if path.startswith("contracts/"):
            selection["contract"] = True
            selection["backend"] = True
            selection["frontend"] = True
        elif path.startswith("supabase/"):
            selection["database"] = True
            selection["backend"] = True
        elif path.startswith("web/"):
            selection["frontend"] = True
        elif path.startswith(("src/", "tests/")) or path in {
            "pyproject.toml",
            "requirements.txt",
            ".python-version",
            ".env.example",
        }:
            selection["backend"] = True
        elif path == "scripts/export_openapi.py":
            selection["backend"] = True
            selection["contract"] = True
            selection["frontend"] = True
        elif path.startswith("scripts/") or path == ".gitignore":
            return _all_components()
        elif path.startswith("development-plans/") or path.endswith((".md", ".mdx")):
            selection["docs"] = True
        else:
            return _all_components()

    return selection


def changed_paths(base: str, head: str) -> list[str]:
    """Read changed paths from Git; raise when the comparison cannot be made."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", base, head, "--"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="paths to classify directly")
    parser.add_argument("--base", help="base Git revision")
    parser.add_argument("--head", help="head Git revision")
    parser.add_argument("--github-output", type=Path, help="append GitHub Actions outputs")
    return parser


def _write_github_output(output: Path, selection: Selection) -> None:
    with output.open("a", encoding="utf-8", newline="\n") as stream:
        for component in COMPONENTS:
            value = "true" if selection[component] else "false"
            stream.write(f"{component}={value}\n")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if bool(args.base) != bool(args.head):
        print("--base and --head must be supplied together", file=sys.stderr)
        return 2

    if args.paths and args.base:
        print("pass direct paths or a Git range, not both", file=sys.stderr)
        return 2

    selection: Selection
    if args.base:
        try:
            paths = changed_paths(args.base, args.head)
            selection = classify_paths(paths)
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"Unable to determine changes; running every check: {error}", file=sys.stderr)
            selection = _all_components()
    elif args.paths:
        selection = classify_paths(args.paths)
    else:
        selection = _all_components()

    if args.github_output:
        _write_github_output(args.github_output, selection)
    print(json.dumps(selection, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
