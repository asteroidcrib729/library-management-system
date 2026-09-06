"""Configuration owned by the HTTP delivery adapter."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from urllib.parse import urlsplit

COOKIE_NAME_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


class Environment(StrEnum):
    """Supported runtime environment identities."""

    LOCAL = "local"
    TEST = "test"
    PREVIEW = "preview"
    STAGING = "staging"
    PRODUCTION = "production"


class ApiConfigurationError(ValueError):
    """Raised when HTTP runtime configuration crosses a safety boundary."""


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Validated HTTP settings without secret serialization or side effects."""

    environment: Environment = Environment.LOCAL
    allowed_origins: tuple[str, ...] = ("http://localhost:3000",)
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str | None = field(default=None, repr=False)
    session_cookie_name: str = "lms_session"
    csrf_cookie_name: str = "lms_csrf"
    session_idle_minutes: int = 30
    session_absolute_hours: int = 12
    login_rate_limit: int = 5
    mutation_rate_limit: int = 120
    rate_window_seconds: int = 60
    maximum_body_bytes: int = 65_536

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ApiConfigurationError("LMS_API_PORT must be between 1 and 65535.")
        if not self.allowed_origins:
            raise ApiConfigurationError("At least one exact LMS_ALLOWED_ORIGINS value is required.")
        for origin in self.allowed_origins:
            self._validate_origin(origin)
        if (
            not COOKIE_NAME_PATTERN.fullmatch(self.session_cookie_name)
            or not COOKIE_NAME_PATTERN.fullmatch(self.csrf_cookie_name)
            or self.session_cookie_name == self.csrf_cookie_name
        ):
            raise ApiConfigurationError("Session and CSRF cookie names must be distinct tokens.")
        if not 5 <= self.session_idle_minutes <= 1440:
            raise ApiConfigurationError("Session idle minutes must be between 5 and 1440.")
        if not 1 <= self.session_absolute_hours <= 168:
            raise ApiConfigurationError("Session absolute hours must be between 1 and 168.")
        if self.session_idle_timeout > self.session_absolute_timeout:
            raise ApiConfigurationError("Session idle timeout cannot exceed absolute timeout.")
        if not 1 <= self.login_rate_limit <= 100:
            raise ApiConfigurationError("Login rate limit must be between 1 and 100.")
        if not 1 <= self.mutation_rate_limit <= 10_000:
            raise ApiConfigurationError("Mutation rate limit must be between 1 and 10000.")
        if not 1 <= self.rate_window_seconds <= 3600:
            raise ApiConfigurationError("Rate window must be between 1 and 3600 seconds.")
        if not 1024 <= self.maximum_body_bytes <= 1_048_576:
            raise ApiConfigurationError("Maximum body size must be between 1024 and 1048576 bytes.")
        if self.environment in {Environment.LOCAL, Environment.TEST}:
            self._validate_local_database_url()

    @classmethod
    def from_environment(cls) -> ApiSettings:
        """Read settings from environment variables without loading files implicitly."""
        raw_environment = os.environ.get("LMS_ENVIRONMENT", Environment.LOCAL.value)
        try:
            environment = Environment(raw_environment.strip().lower())
        except ValueError as error:
            choices = ", ".join(item.value for item in Environment)
            raise ApiConfigurationError(f"LMS_ENVIRONMENT must be one of: {choices}.") from error

        default_origins = "http://localhost:3000" if environment is Environment.LOCAL else ""
        origins = tuple(
            value.strip()
            for value in os.environ.get("LMS_ALLOWED_ORIGINS", default_origins).split(",")
            if value.strip()
        )
        raw_port = os.environ.get("LMS_API_PORT", "8000")
        try:
            port = int(raw_port)
        except ValueError as error:
            raise ApiConfigurationError("LMS_API_PORT must be an integer.") from error

        return cls(
            environment=environment,
            allowed_origins=origins,
            host=os.environ.get("LMS_API_HOST", "127.0.0.1").strip(),
            port=port,
            database_url=os.environ.get("DATABASE_URL") or None,
            session_cookie_name=os.environ.get("LMS_SESSION_COOKIE", "lms_session"),
            csrf_cookie_name=os.environ.get("LMS_CSRF_COOKIE", "lms_csrf"),
            session_idle_minutes=_integer_environment("LMS_SESSION_IDLE_MINUTES", 30),
            session_absolute_hours=_integer_environment("LMS_SESSION_ABSOLUTE_HOURS", 12),
            login_rate_limit=_integer_environment("LMS_LOGIN_RATE_LIMIT", 5),
            mutation_rate_limit=_integer_environment("LMS_MUTATION_RATE_LIMIT", 120),
            rate_window_seconds=_integer_environment("LMS_RATE_WINDOW_SECONDS", 60),
            maximum_body_bytes=_integer_environment("LMS_MAX_BODY_BYTES", 65_536),
        )

    @property
    def session_idle_timeout(self) -> timedelta:
        return timedelta(minutes=self.session_idle_minutes)

    @property
    def session_absolute_timeout(self) -> timedelta:
        return timedelta(hours=self.session_absolute_hours)

    @property
    def secure_cookies(self) -> bool:
        return self.environment in {
            Environment.PREVIEW,
            Environment.STAGING,
            Environment.PRODUCTION,
        }

    def _validate_origin(self, origin: str) -> None:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ApiConfigurationError(f"Invalid allowed origin: {origin!r}.")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ApiConfigurationError(
                "Allowed origins must not contain paths, queries, or fragments."
            )
        if (
            self.environment in {Environment.STAGING, Environment.PRODUCTION}
            and parsed.scheme != "https"
        ):
            raise ApiConfigurationError("Staging and production origins must use HTTPS.")
        if self.environment in {Environment.LOCAL, Environment.TEST} and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
            "testserver",
        }:
            raise ApiConfigurationError("Local and test origins must resolve to the local machine.")

    def _validate_local_database_url(self) -> None:
        if self.database_url is None:
            return
        parsed = urlsplit(self.database_url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ApiConfigurationError(
                "Local and test environments may not use a remote DATABASE_URL."
            )


def _integer_environment(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError as error:
        raise ApiConfigurationError(f"{name} must be an integer.") from error
