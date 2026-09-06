from fastapi import FastAPI
from fastapi.testclient import TestClient

from library_management.api import create_app
from library_management.api.config import ApiSettings, Environment
from library_management.api.health import ProbeResult, ReadinessProbe
from library_management.postgres.database import TransactionBusyError


def test_liveness_reports_process_metadata() -> None:
    client = TestClient(_test_app())

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "environment": "test",
        "checks": [],
    }


def test_readiness_fails_closed_until_postgresql_probe_exists() -> None:
    client = TestClient(_test_app())

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert response.json()["status"] == "unavailable"
    assert response.json()["checks"] == [
        {
            "name": "postgresql",
            "ready": False,
            "detail": "PostgreSQL is not configured.",
        }
    ]


def test_readiness_succeeds_when_all_injected_probes_are_ready() -> None:
    app = _test_app(
        readiness_probes=(
            lambda: ProbeResult("postgresql", True, "available"),
            lambda: ProbeResult("schema", True, "compatible"),
        )
    )
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert [check["name"] for check in response.json()["checks"]] == [
        "postgresql",
        "schema",
    ]


def test_cors_allows_only_the_configured_local_origin() -> None:
    client = TestClient(_test_app())

    accepted = client.options(
        "/health/live",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    rejected = client.options(
        "/health/live",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert accepted.status_code == 200
    assert accepted.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert accepted.headers["access-control-allow-credentials"] == "true"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_hosted_responses_expose_safe_timing_and_security_headers() -> None:
    app = create_app(
        ApiSettings(
            environment=Environment.STAGING,
            allowed_origins=("https://app.staging.example",),
        ),
        readiness_probes=(lambda: ProbeResult("postgresql", True, "available"),),
    )
    client = TestClient(app)

    response = client.get(
        "/health/ready",
        headers={"Origin": "https://app.staging.example"},
    )

    assert response.status_code == 200
    assert response.headers["server-timing"].startswith("app;dur=")
    assert ", db;dur=" in response.headers["server-timing"]
    assert response.headers["timing-allow-origin"] == "https://app.staging.example"
    assert response.headers["access-control-expose-headers"] == "Server-Timing, X-Request-ID"
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_openapi_contract_contains_health_and_versioned_capabilities() -> None:
    contract = _test_app().openapi()

    assert contract["info"]["version"] == "0.1.0"
    assert {"/health/live", "/health/ready", "/api/v1/auth/login"} <= set(contract["paths"])
    assert all(path.startswith(("/health/", "/api/v1/")) for path in contract["paths"])


def test_api_maps_dependency_and_overload_failures_without_internal_details() -> None:
    app = _test_app()

    @app.get("/synthetic-busy")
    def synthetic_busy() -> None:
        raise TransactionBusyError("internal pool details")

    client = TestClient(app)
    unavailable = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:3000"},
        json={"username": "valid.user", "password": "not-a-secret"},
    )
    busy = client.get("/synthetic-busy")

    assert unavailable.status_code == 503
    assert unavailable.json()["code"] == "database_unavailable"
    assert unavailable.headers["retry-after"] == "5"
    assert busy.status_code == 503
    assert busy.json()["code"] == "database_busy"
    assert "internal pool details" not in busy.text


def test_api_rejects_oversized_declared_payload_before_processing() -> None:
    client = TestClient(_test_app())

    response = client.post(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Content-Length": "1000000",
        },
        content=b"{}",
    )

    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


def _test_app(*, readiness_probes: tuple[ReadinessProbe, ...] = ()) -> FastAPI:
    return create_app(
        ApiSettings(
            environment=Environment.TEST,
            allowed_origins=("http://localhost:3000",),
        ),
        readiness_probes=readiness_probes,
    )
