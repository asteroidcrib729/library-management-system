"""Small browser-security middleware independent of business handlers."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.responses import Response

from library_management.api.config import ApiSettings

logger = logging.getLogger(__name__)


def install_request_middleware(application: FastAPI, settings: ApiSettings) -> None:
    @application.middleware("http")
    async def browser_boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        supplied_id = request.headers.get("X-Request-ID", "")
        request.state.request_id = (
            supplied_id if 1 <= len(supplied_id) <= 100 and supplied_id.isascii() else uuid4().hex
        )
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            if origin not in settings.allowed_origins:
                response = _middleware_error(
                    request, 403, "origin_rejected", "Origin is not allowed."
                )
                return _finalize_response(response, request, settings, started)
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                too_large = int(content_length) > settings.maximum_body_bytes
            except ValueError:
                too_large = True
            if too_large:
                response = _middleware_error(
                    request,
                    status.HTTP_413_CONTENT_TOO_LARGE,
                    "payload_too_large",
                    "Request body exceeds the configured limit.",
                )
                return _finalize_response(response, request, settings, started)
        response = await call_next(request)
        return _finalize_response(response, request, settings, started)


def _finalize_response(
    response: Response,
    request: Request,
    settings: ApiSettings,
    started: float,
) -> Response:
    """Apply observable, credential-safe browser headers to every API response."""

    duration_ms = (time.perf_counter() - started) * 1000
    timing = [f"app;dur={duration_ms:.2f}"]
    database_duration = getattr(request.state, "database_probe_duration_ms", None)
    if isinstance(database_duration, float):
        timing.append(f"db;dur={database_duration:.2f}")
    response.headers["Server-Timing"] = ", ".join(timing)
    origin = request.headers.get("Origin")
    if origin in settings.allowed_origins:
        response.headers["Timing-Allow-Origin"] = origin
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = (
        "no-store"
        if request.url.path.startswith("/api/v1/auth")
        else response.headers.get("Cache-Control", "private, no-store")
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if settings.secure_cookies:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    logger.info(
        "http_request method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request.state.request_id,
    )
    return response


def _middleware_error(
    request: Request, response_status: int, code: str, message: str
) -> JSONResponse:
    return JSONResponse(
        status_code=response_status,
        content={"code": code, "message": message, "request_id": request.state.request_id},
        headers={"X-Request-ID": request.state.request_id},
    )
