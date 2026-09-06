"""Deterministic OpenAPI rendering used by local tooling and CI."""

from __future__ import annotations

import json

from library_management.api.app import create_app
from library_management.api.config import ApiSettings, Environment


def render_contract() -> str:
    """Return stable, reviewable JSON for the current API contract."""
    application = create_app(
        ApiSettings(
            environment=Environment.TEST,
            allowed_origins=("http://testserver",),
        )
    )
    return json.dumps(application.openapi(), indent=2, sort_keys=True) + "\n"
