"""Liveness and dependency-aware readiness endpoints."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from library_management import __version__
from library_management.api.config import ApiSettings


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Internal result returned by one readiness dependency probe."""

    name: str
    ready: bool
    detail: str


ReadinessProbe = Callable[[], ProbeResult]


class HealthCheck(BaseModel):
    """Public status of one dependency without sensitive details."""

    model_config = ConfigDict(frozen=True)

    name: str
    ready: bool
    detail: str


class HealthResponse(BaseModel):
    """Stable health response shared by liveness and readiness."""

    model_config = ConfigDict(frozen=True)

    status: str
    version: str
    environment: str
    checks: tuple[HealthCheck, ...] = ()


def get_settings(request: Request) -> ApiSettings:
    return request.app.state.api_settings


def create_health_router() -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health/live", response_model=HealthResponse)
    def liveness(
        settings: Annotated[ApiSettings, Depends(get_settings)],
    ) -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=__version__,
            environment=settings.environment.value,
        )

    @router.get(
        "/health/ready",
        response_model=HealthResponse,
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
    )
    def readiness(request: Request) -> HealthResponse | JSONResponse:
        settings: ApiSettings = request.app.state.api_settings
        probes: tuple[ReadinessProbe, ...] = request.app.state.readiness_probes
        probe_started = time.perf_counter()
        results = tuple(probe() for probe in probes)
        request.state.database_probe_duration_ms = (time.perf_counter() - probe_started) * 1000
        if not results:
            results = (
                ProbeResult(
                    name="postgresql",
                    ready=False,
                    detail="PostgreSQL is not configured.",
                ),
            )
        response = HealthResponse(
            status="ready" if all(result.ready for result in results) else "unavailable",
            version=__version__,
            environment=settings.environment.value,
            checks=tuple(
                HealthCheck(name=item.name, ready=item.ready, detail=item.detail)
                for item in results
            ),
        )
        if response.status == "ready":
            return response
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
            headers={"Retry-After": "5"},
        )

    return router
