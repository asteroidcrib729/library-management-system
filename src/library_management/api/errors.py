"""Stable public error mapping with no persistence or credential leakage."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from library_management.domain import DomainValidationError
from library_management.postgres.database import (
    DatabaseUnavailableError,
    TransactionBusyError,
)
from library_management.repositories.postgres.idempotency import IdempotencyConflictError
from library_management.services import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    CatalogConflictError,
    CatalogNotFoundError,
    CirculationNotFoundError,
    EngagementNotFoundError,
    FinancialNotFoundError,
)


def install_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(HTTPException)
    def http_error(request: Request, error: HTTPException) -> JSONResponse:
        code = {
            400: "bad_request",
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            413: "payload_too_large",
            429: "rate_limited",
            503: "service_unavailable",
        }.get(error.status_code, "http_error")
        return _response(request, error.status_code, code, str(error.detail), error.headers)

    @application.exception_handler(RequestValidationError)
    def request_validation(request: Request, error: RequestValidationError) -> JSONResponse:
        del error
        return _response(
            request,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            "The request did not satisfy the API contract.",
        )

    @application.exception_handler(DomainValidationError)
    def domain_validation(request: Request, error: DomainValidationError) -> JSONResponse:
        return _response(request, 422, "validation_error", str(error))

    @application.exception_handler(AuthenticationError)
    def authentication(request: Request, error: AuthenticationError) -> JSONResponse:
        return _response(request, 401, "invalid_credentials", str(error))

    @application.exception_handler(AuthorizationError)
    def authorization(request: Request, error: AuthorizationError) -> JSONResponse:
        return _response(request, 403, "forbidden", str(error))

    not_found_errors = (
        CatalogNotFoundError,
        CirculationNotFoundError,
        EngagementNotFoundError,
        FinancialNotFoundError,
    )

    @application.exception_handler(ApplicationError)
    def application_error(request: Request, error: ApplicationError) -> JSONResponse:
        code = "not_found" if isinstance(error, not_found_errors) else "conflict"
        response_status = 404 if code == "not_found" else 409
        if isinstance(error, CatalogConflictError):
            response_status = 409
        return _response(request, response_status, code, str(error))

    @application.exception_handler(IdempotencyConflictError)
    def idempotency_conflict(request: Request, error: IdempotencyConflictError) -> JSONResponse:
        return _response(request, 409, "idempotency_conflict", str(error))

    @application.exception_handler(TransactionBusyError)
    def database_busy(request: Request, error: TransactionBusyError) -> JSONResponse:
        del error
        return _response(
            request,
            503,
            "database_busy",
            "The database is busy; retry the complete request later.",
            {"Retry-After": "2"},
        )

    @application.exception_handler(DatabaseUnavailableError)
    def database_unavailable(request: Request, error: DatabaseUnavailableError) -> JSONResponse:
        del error
        return _response(
            request,
            503,
            "database_unavailable",
            "The database is temporarily unavailable.",
            {"Retry-After": "5"},
        )


def _response(
    request: Request,
    response_status: int,
    code: str,
    message: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or uuid4().hex
    return JSONResponse(
        status_code=response_status,
        content={"code": code, "message": message, "request_id": request_id},
        headers=headers,
    )
