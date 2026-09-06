"""FastAPI application factory with no database or filesystem side effects."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from library_management import __version__
from library_management.api.config import ApiSettings
from library_management.api.errors import install_error_handlers
from library_management.api.health import ProbeResult, ReadinessProbe, create_health_router
from library_management.api.middleware import install_request_middleware
from library_management.api.routes import create_api_router
from library_management.api.security import SlidingWindowRateLimiter
from library_management.api.sessions import BrowserSessionStore
from library_management.postgres import PostgresDatabase, PostgresSettings
from library_management.repositories.postgres import PostgresUnitOfWork
from library_management.security import PasswordService
from library_management.services import AuthenticationService


def create_app(
    settings: ApiSettings | None = None,
    *,
    readiness_probes: Iterable[ReadinessProbe] = (),
) -> FastAPI:
    """Create an isolated ASGI application for one configured environment."""
    resolved_settings = settings or ApiSettings.from_environment()
    database = (
        PostgresDatabase(
            PostgresSettings.from_environment(
                resolved_settings.database_url, resolved_settings.environment.value
            )
        )
        if resolved_settings.database_url
        else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        if database is not None:
            await run_in_threadpool(database.open)
        try:
            yield
        finally:
            if database is not None:
                await run_in_threadpool(database.close)

    def postgres_probe() -> ProbeResult:
        ready = database is not None and database.schema_ready()
        return ProbeResult(
            "postgresql",
            ready,
            "Database and schema are available."
            if ready
            else "Database unavailable or schema incompatible.",
        )

    application = FastAPI(
        title="Library Management System API",
        summary="Versioned HTTP delivery adapter for the library management system.",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    application.state.api_settings = resolved_settings
    application.state.database = database
    password_service = PasswordService()
    application.state.password_service = password_service
    application.state.authentication_service = (
        AuthenticationService(
            lambda: PostgresUnitOfWork(database),
            password_service,
        )
        if database is not None
        else None
    )
    application.state.session_store = (
        BrowserSessionStore(
            database,
            idle_timeout=resolved_settings.session_idle_timeout,
            absolute_timeout=resolved_settings.session_absolute_timeout,
        )
        if database is not None
        else None
    )
    application.state.rate_limiter = SlidingWindowRateLimiter()
    application.state.readiness_probes = tuple(readiness_probes) + (
        (postgres_probe,) if database is not None else ()
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Content-Type",
            "Idempotency-Key",
            "Origin",
            "X-CSRF-Token",
            "X-Request-ID",
        ],
        expose_headers=["Server-Timing", "X-Request-ID"],
    )
    install_request_middleware(application, resolved_settings)
    install_error_handlers(application)
    application.include_router(create_health_router())
    application.include_router(create_api_router())
    return application


app = create_app()
