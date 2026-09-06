"""Browser request authentication, CSRF checks, and bounded rate controls."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from library_management.api.config import ApiSettings
from library_management.api.sessions import ActiveSession, BrowserSessionStore
from library_management.postgres import PostgresDatabase
from library_management.postgres.database import DatabaseUnavailableError


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    retry_after: int


class SlidingWindowRateLimiter:
    """A bounded single-process limiter suitable for the initial Render instance."""

    def __init__(self, *, max_keys: int = 10_000) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def consume(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        threshold = now - window_seconds
        with self._lock:
            if key not in self._events and len(self._events) >= self._max_keys:
                oldest = next(iter(self._events))
                del self._events[oldest]
            events = self._events[key]
            while events and events[0] <= threshold:
                events.popleft()
            if len(events) >= limit:
                return RateLimitResult(False, max(1, int(events[0] + window_seconds - now) + 1))
            events.append(now)
            return RateLimitResult(True, 0)


def get_settings(request: Request) -> ApiSettings:
    return request.app.state.api_settings


def get_database(request: Request) -> PostgresDatabase:
    database: PostgresDatabase | None = request.app.state.database
    if database is None:
        raise DatabaseUnavailableError("Database is unavailable.")
    return database


def get_session_store(request: Request) -> BrowserSessionStore:
    store: BrowserSessionStore | None = request.app.state.session_store
    if store is None:
        raise DatabaseUnavailableError("Session storage is unavailable.")
    return store


def get_active_session(
    request: Request,
    settings: Annotated[ApiSettings, Depends(get_settings)],
    store: Annotated[BrowserSessionStore, Depends(get_session_store)],
) -> ActiveSession:
    token = request.cookies.get(settings.session_cookie_name)
    active = store.resolve(token) if token else None
    if active is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication is required.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_header = request.headers.get("X-CSRF-Token")
        csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
        if (
            not csrf_header
            or not csrf_cookie
            or csrf_header != csrf_cookie
            or not active.csrf_matches(csrf_header)
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF validation failed.")
        limiter: SlidingWindowRateLimiter = request.app.state.rate_limiter
        result = limiter.consume(
            f"mutation:{active.principal.user_id}",
            limit=settings.mutation_rate_limit,
            window_seconds=settings.rate_window_seconds,
        )
        if not result.allowed:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Mutation rate limit exceeded.",
                headers={"Retry-After": str(result.retry_after)},
            )
    return active


CurrentSession = Annotated[ActiveSession, Depends(get_active_session)]
