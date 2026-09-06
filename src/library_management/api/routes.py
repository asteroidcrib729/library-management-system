"""Versioned capability routers around framework-neutral application services."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse

from library_management.api.config import ApiSettings
from library_management.api.execution import execute_idempotent, idempotency_key
from library_management.api.models import (
    AccountRequest,
    AcquiredRequest,
    AcquisitionRequestBody,
    BookCopyResponse,
    BookRequestBody,
    BookRequestViewResponse,
    BookResponse,
    CatalogEntryResponse,
    CheckoutRequest,
    CopyRequest,
    CopyStatusRequest,
    DeactivateAccountRequest,
    FeedbackRequest,
    FeedbackViewResponse,
    FineViewResponse,
    LoanViewResponse,
    LoginRequest,
    ManualFineRequest,
    NoteRequest,
    OperationalReportResponse,
    PopularBookResponse,
    PrincipalResponse,
    RecommendationResponse,
    ReservationViewResponse,
    ReturnRequest,
    ReviewRequest,
    SessionResponse,
    WaiverRequest,
)
from library_management.api.security import (
    CurrentSession,
    SlidingWindowRateLimiter,
    get_database,
    get_session_store,
    get_settings,
)
from library_management.api.sessions import BrowserSessionStore
from library_management.domain import FeedbackStatus, RequestStatus
from library_management.postgres import PostgresDatabase
from library_management.repositories.postgres.unit_of_work import (
    BorrowedPostgresUnitOfWork,
    PostgresUnitOfWork,
)
from library_management.security import PasswordService
from library_management.services import (
    AccountService,
    AuthenticationService,
    CatalogService,
    CirculationService,
    EngagementService,
    FinancialService,
    InsightsService,
)

Database = Annotated[PostgresDatabase, Depends(get_database)]
Settings = Annotated[ApiSettings, Depends(get_settings)]
SessionStore = Annotated[BrowserSessionStore, Depends(get_session_store)]


def create_api_router() -> APIRouter:
    root = APIRouter(prefix="/api/v1")
    root.include_router(_auth_router())
    root.include_router(_accounts_router())
    root.include_router(_catalog_router())
    root.include_router(_circulation_router())
    root.include_router(_financial_router())
    root.include_router(_engagement_router())
    root.include_router(_insights_router())
    return root


def _factory(database: PostgresDatabase):
    return partial(PostgresUnitOfWork, database)


def _auth_router() -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["authentication"])

    @router.post("/login", response_model=SessionResponse)
    def login(
        body: LoginRequest,
        request: Request,
        response: Response,
        database: Database,
        settings: Settings,
        sessions: SessionStore,
    ) -> SessionResponse:
        client = request.client.host if request.client else "unknown"
        limiter: SlidingWindowRateLimiter = request.app.state.rate_limiter
        rate = limiter.consume(
            f"login:{client}:{body.username.strip().casefold()}",
            limit=settings.login_rate_limit,
            window_seconds=settings.rate_window_seconds,
        )
        if not rate.allowed:
            from fastapi import HTTPException

            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Login rate limit exceeded.",
                headers={"Retry-After": str(rate.retry_after)},
            )
        authentication: AuthenticationService = request.app.state.authentication_service
        principal = authentication.authenticate(body.username, body.password)
        issued = sessions.create(principal)
        max_age = settings.session_absolute_hours * 3600
        response.set_cookie(
            settings.session_cookie_name,
            issued.session_token,
            max_age=max_age,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            settings.csrf_cookie_name,
            issued.csrf_token,
            max_age=max_age,
            httponly=False,
            secure=settings.secure_cookies,
            samesite="lax",
            path="/api/v1",
        )
        return SessionResponse(
            principal=PrincipalResponse.model_validate(principal),
            csrf_token=issued.csrf_token,
            expires_at=issued.expires_at,
        )

    @router.get("/session", response_model=SessionResponse)
    def current_session(
        current: CurrentSession,
        request: Request,
        settings: Settings,
    ) -> SessionResponse:
        csrf = request.cookies.get(settings.csrf_cookie_name)
        if csrf is None or not current.csrf_matches(csrf):
            from fastapi import HTTPException

            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication is required.")
        return SessionResponse(
            principal=PrincipalResponse.model_validate(current.principal),
            csrf_token=csrf,
            expires_at=current.expires_at,
        )

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(
        current: CurrentSession,
        request: Request,
        response: Response,
        settings: Settings,
        sessions: SessionStore,
    ) -> None:
        del current
        token = request.cookies.get(settings.session_cookie_name)
        if token:
            sessions.revoke(token)
        response.delete_cookie(settings.session_cookie_name, path="/")
        response.delete_cookie(settings.csrf_cookie_name, path="/api/v1")

    return router


def _accounts_router() -> APIRouter:
    router = APIRouter(prefix="/accounts", tags=["accounts"])

    @router.post("/register", response_model=PrincipalResponse, status_code=201)
    def register(
        body: AccountRequest,
        request: Request,
        database: Database,
        settings: Settings,
    ) -> Any:
        _limit_public_credential(request, settings, f"register:{body.username.casefold()}")
        password_service: PasswordService = request.app.state.password_service
        return AccountService(_factory(database), password_service).register_member(
            body.display_name, body.username, body.password
        )

    @router.post("/bootstrap-administrator", response_model=PrincipalResponse, status_code=201)
    def bootstrap(
        body: AccountRequest,
        request: Request,
        database: Database,
        settings: Settings,
    ) -> Any:
        _limit_public_credential(request, settings, "bootstrap")
        password_service: PasswordService = request.app.state.password_service
        return AccountService(_factory(database), password_service).bootstrap_administrator(
            body.display_name, body.username, body.password
        )

    @router.post("/librarians", response_model=PrincipalResponse, status_code=201)
    def create_librarian(
        body: AccountRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            "accounts.create_librarian",
            body,
            PrincipalResponse,
            lambda unit: AccountService(
                lambda: unit, request.app.state.password_service
            ).create_librarian(
                current.principal.user_id, body.display_name, body.username, body.password
            ),
            201,
        )

    @router.post("/deactivate", response_model=PrincipalResponse)
    def deactivate(
        body: DeactivateAccountRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            "accounts.deactivate",
            body,
            PrincipalResponse,
            lambda unit: AccountService(
                lambda: unit, request.app.state.password_service
            ).deactivate_account(current.principal.user_id, body.username),
        )

    return router


def _catalog_router() -> APIRouter:
    router = APIRouter(prefix="/catalog", tags=["catalog"])

    @router.get("/books", response_model=list[CatalogEntryResponse])
    def browse(
        current: CurrentSession,
        database: Database,
        query: Annotated[str | None, Query(max_length=200)] = None,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> Any:
        results = CatalogService(_factory(database)).browse(current.principal.user_id, query)
        return results[offset : offset + limit]

    @router.get("/books/{book_id}", response_model=CatalogEntryResponse)
    def get_book(book_id: int, current: CurrentSession, database: Database) -> Any:
        return CatalogService(_factory(database)).get_book(current.principal.user_id, book_id)

    @router.get("/books/{book_id}/copies", response_model=list[BookCopyResponse])
    def list_copies(
        book_id: int,
        current: CurrentSession,
        database: Database,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> Any:
        results = CatalogService(_factory(database)).list_copies(current.principal.user_id, book_id)
        return results[offset : offset + limit]

    @router.post("/books", response_model=BookResponse, status_code=201)
    def add_book(
        body: BookRequestBody,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            "catalog.add_book",
            body,
            BookResponse,
            lambda unit: CatalogService(lambda: unit).add_book(
                current.principal.user_id,
                body.title,
                body.author,
                body.publication_year,
                isbn=body.isbn,
                category=body.category,
                description=body.description,
            ),
            201,
        )

    @router.put("/books/{book_id}", response_model=BookResponse)
    def update_book(
        book_id: int,
        body: BookRequestBody,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"catalog.update_book:{book_id}",
            body,
            BookResponse,
            lambda unit: CatalogService(lambda: unit).update_book(
                current.principal.user_id,
                book_id,
                body.title,
                body.author,
                body.publication_year,
                isbn=body.isbn,
                category=body.category,
                description=body.description,
            ),
        )

    @router.post("/books/{book_id}/copies", response_model=BookCopyResponse, status_code=201)
    def add_copy(
        book_id: int,
        body: CopyRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"catalog.add_copy:{book_id}",
            body,
            BookCopyResponse,
            lambda unit: CatalogService(lambda: unit).add_copy(
                current.principal.user_id, book_id, body.barcode
            ),
            201,
        )

    @router.patch("/copies/{barcode}", response_model=BookCopyResponse)
    def update_copy(
        barcode: str,
        body: CopyStatusRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"catalog.update_copy:{barcode}",
            body,
            BookCopyResponse,
            lambda unit: CatalogService(lambda: unit).update_copy_status(
                current.principal.user_id, barcode, body.status
            ),
        )

    return router


def _circulation_router() -> APIRouter:
    router = APIRouter(prefix="/circulation", tags=["circulation"])

    @router.get("/reservations", response_model=list[ReservationViewResponse])
    def reservations(
        current: CurrentSession,
        database: Database,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> Any:
        results = CirculationService(_factory(database)).list_reservations(
            current.principal.user_id
        )
        return results[offset : offset + limit]

    @router.post(
        "/reservations/books/{book_id}", response_model=ReservationViewResponse, status_code=201
    )
    def reserve(
        book_id: int, request: Request, current: CurrentSession, database: Database
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"circulation.reserve:{book_id}",
            {"book_id": book_id},
            ReservationViewResponse,
            lambda unit: CirculationService(lambda: unit).reserve(
                current.principal.user_id, book_id
            ),
            201,
        )

    @router.post("/reservations/{reservation_id}/cancel", response_model=ReservationViewResponse)
    def cancel(
        reservation_id: int,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"circulation.cancel:{reservation_id}",
            {"reservation_id": reservation_id},
            ReservationViewResponse,
            lambda unit: CirculationService(lambda: unit).cancel_reservation(
                current.principal.user_id, reservation_id
            ),
        )

    @router.get("/loans", response_model=list[LoanViewResponse])
    def loans(
        current: CurrentSession,
        database: Database,
        username: Annotated[str | None, Query(max_length=32)] = None,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> Any:
        results = CirculationService(_factory(database)).list_loans(
            current.principal.user_id, username
        )
        return results[offset : offset + limit]

    @router.post("/loans/checkout", response_model=LoanViewResponse, status_code=201)
    def checkout(
        body: CheckoutRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            "circulation.checkout",
            body,
            LoanViewResponse,
            lambda unit: CirculationService(lambda: unit).checkout(
                current.principal.user_id, body.borrower_username, body.barcode
            ),
            201,
        )

    @router.post("/loans/return", response_model=LoanViewResponse)
    def return_copy(
        body: ReturnRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            "circulation.return",
            body,
            LoanViewResponse,
            lambda unit: CirculationService(lambda: unit).return_copy(
                current.principal.user_id, body.barcode
            ),
        )

    @router.post("/loans/{loan_id}/renew", response_model=LoanViewResponse)
    def renew(
        loan_id: int, request: Request, current: CurrentSession, database: Database
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"circulation.renew:{loan_id}",
            {"loan_id": loan_id},
            LoanViewResponse,
            lambda unit: CirculationService(lambda: unit).renew(current.principal.user_id, loan_id),
        )

    return router


def _financial_router() -> APIRouter:
    router = APIRouter(prefix="/finance", tags=["finance"])

    @router.get("/fines", response_model=list[FineViewResponse])
    def fines(
        current: CurrentSession,
        database: Database,
        username: Annotated[str | None, Query(max_length=32)] = None,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> Any:
        results = FinancialService(_factory(database)).list_fines(
            current.principal.user_id, username
        )
        return results[offset : offset + limit]

    @router.get("/fines/{fine_id}", response_model=FineViewResponse)
    def fine(fine_id: int, current: CurrentSession, database: Database) -> Any:
        return FinancialService(_factory(database)).get_fine(current.principal.user_id, fine_id)

    @router.post("/fines", response_model=FineViewResponse, status_code=201)
    def assess(
        body: ManualFineRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            "finance.assess",
            body,
            FineViewResponse,
            lambda unit: FinancialService(lambda: unit).assess_manual(
                current.principal.user_id, body.username, body.amount, body.reason
            ),
            201,
        )

    @router.post("/fines/{fine_id}/payment", response_model=FineViewResponse)
    def pay(
        fine_id: int,
        body: NoteRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"finance.pay:{fine_id}",
            body,
            FineViewResponse,
            lambda unit: FinancialService(lambda: unit).record_payment(
                current.principal.user_id, fine_id, body.note
            ),
        )

    @router.post("/fines/{fine_id}/waiver", response_model=FineViewResponse)
    def waive(
        fine_id: int,
        body: WaiverRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"finance.waive:{fine_id}",
            body,
            FineViewResponse,
            lambda unit: FinancialService(lambda: unit).waive(
                current.principal.user_id, fine_id, body.reason
            ),
        )

    return router


def _engagement_router() -> APIRouter:
    router = APIRouter(prefix="/engagement", tags=["engagement"])

    @router.get("/book-requests", response_model=list[BookRequestViewResponse])
    def book_requests(
        current: CurrentSession,
        database: Database,
        request_status: Annotated[RequestStatus | None, Query(alias="status")] = None,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> Any:
        results = EngagementService(_factory(database)).list_book_requests(
            current.principal.user_id, request_status
        )
        return results[offset : offset + limit]

    @router.post("/book-requests", response_model=BookRequestViewResponse, status_code=201)
    def submit_request(
        body: AcquisitionRequestBody,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            "engagement.request",
            body,
            BookRequestViewResponse,
            lambda unit: EngagementService(lambda: unit).submit_book_request(
                current.principal.user_id, body.title, body.author, body.publication_year
            ),
            201,
        )

    @router.post("/book-requests/{request_id}/review", response_model=BookRequestViewResponse)
    def review_request(
        request_id: int,
        body: ReviewRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"engagement.review_request:{request_id}",
            body,
            BookRequestViewResponse,
            lambda unit: EngagementService(lambda: unit).review_book_request(
                current.principal.user_id, request_id, body.status, body.note
            ),
        )

    @router.post("/book-requests/{request_id}/acquire", response_model=BookRequestViewResponse)
    def acquire_request(
        request_id: int,
        body: AcquiredRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"engagement.acquire_request:{request_id}",
            body,
            BookRequestViewResponse,
            lambda unit: EngagementService(lambda: unit).mark_request_acquired(
                current.principal.user_id, request_id, body.book_id
            ),
        )

    @router.get("/feedback", response_model=list[FeedbackViewResponse])
    def feedback(
        current: CurrentSession,
        database: Database,
        feedback_status: Annotated[FeedbackStatus | None, Query(alias="status")] = None,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> Any:
        results = EngagementService(_factory(database)).list_feedback(
            current.principal.user_id, feedback_status
        )
        return results[offset : offset + limit]

    @router.post("/feedback", response_model=FeedbackViewResponse, status_code=201)
    def submit_feedback(
        body: FeedbackRequest,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            "engagement.feedback",
            body,
            FeedbackViewResponse,
            lambda unit: EngagementService(lambda: unit).submit_feedback(
                current.principal.user_id, body.content
            ),
            201,
        )

    @router.post("/feedback/{feedback_id}/review", response_model=FeedbackViewResponse)
    def review_feedback(
        feedback_id: int,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"engagement.review_feedback:{feedback_id}",
            {"feedback_id": feedback_id},
            FeedbackViewResponse,
            lambda unit: EngagementService(lambda: unit).review_feedback(
                current.principal.user_id, feedback_id
            ),
        )

    @router.post("/feedback/{feedback_id}/archive", response_model=FeedbackViewResponse)
    def archive_feedback(
        feedback_id: int,
        request: Request,
        current: CurrentSession,
        database: Database,
    ) -> JSONResponse:
        return _command(
            request,
            current.principal.user_id,
            database,
            f"engagement.archive_feedback:{feedback_id}",
            {"feedback_id": feedback_id},
            FeedbackViewResponse,
            lambda unit: EngagementService(lambda: unit).archive_feedback(
                current.principal.user_id, feedback_id
            ),
        )

    return router


def _insights_router() -> APIRouter:
    router = APIRouter(prefix="/insights", tags=["insights"])

    @router.get("/recommendations", response_model=list[RecommendationResponse])
    def recommendations(
        current: CurrentSession,
        database: Database,
        limit: Annotated[int | None, Query(ge=1, le=20)] = None,
    ) -> Any:
        return InsightsService(_factory(database)).recommend(current.principal.user_id, limit)

    @router.get("/popular", response_model=list[PopularBookResponse])
    def popular(
        current: CurrentSession,
        database: Database,
        limit: Annotated[int | None, Query(ge=1, le=20)] = None,
    ) -> Any:
        return InsightsService(_factory(database)).popular(current.principal.user_id, limit)

    @router.get("/operations", response_model=OperationalReportResponse)
    def operations(current: CurrentSession, database: Database) -> Any:
        return InsightsService(_factory(database)).operational_report(current.principal.user_id)

    return router


def _command(
    request: Request,
    actor_id: int,
    database: PostgresDatabase,
    operation: str,
    body: Any,
    response_model: type[Any],
    command: Callable[[BorrowedPostgresUnitOfWork], Any],
    response_status: int = 200,
) -> JSONResponse:
    result, stored_status, replayed = execute_idempotent(
        database=database,
        actor_id=actor_id,
        operation=operation,
        key=idempotency_key(request),
        request_body=body,
        command=command,
        response_model=response_model,
        response_status=response_status,
    )
    payload = (
        result
        if isinstance(result, dict)
        else response_model.model_validate(result).model_dump(mode="json", by_alias=True)
    )
    return JSONResponse(
        status_code=stored_status,
        content=payload,
        headers={"Idempotency-Replayed": "true" if replayed else "false"},
    )


def _limit_public_credential(request: Request, settings: ApiSettings, operation: str) -> None:
    from fastapi import HTTPException

    client = request.client.host if request.client else "unknown"
    limiter: SlidingWindowRateLimiter = request.app.state.rate_limiter
    result = limiter.consume(
        f"credential:{client}:{operation}",
        limit=settings.login_rate_limit,
        window_seconds=settings.rate_window_seconds,
    )
    if not result.allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Credential rate limit exceeded.",
            headers={"Retry-After": str(result.retry_after)},
        )
