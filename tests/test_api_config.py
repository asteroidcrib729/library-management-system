import pytest

from library_management.api.config import (
    ApiConfigurationError,
    ApiSettings,
    Environment,
)


def test_local_settings_accept_local_services() -> None:
    settings = ApiSettings(database_url="postgresql://postgres:postgres@127.0.0.1:54322/postgres")

    assert settings.environment is Environment.LOCAL
    assert settings.allowed_origins == ("http://localhost:3000",)


def test_local_settings_reject_remote_database() -> None:
    with pytest.raises(ApiConfigurationError, match="may not use a remote DATABASE_URL"):
        ApiSettings(
            database_url=(
                "postgresql://application:secret@aws-0-region.pooler.supabase.com:5432/postgres"
            )
        )


def test_local_settings_reject_remote_browser_origin() -> None:
    with pytest.raises(ApiConfigurationError, match="must resolve to the local machine"):
        ApiSettings(allowed_origins=("https://preview.example.com",))


def test_production_settings_require_https_origin() -> None:
    with pytest.raises(ApiConfigurationError, match="must use HTTPS"):
        ApiSettings(
            environment=Environment.PRODUCTION,
            allowed_origins=("http://app.example.com",),
        )


def test_cookie_transport_matches_environment() -> None:
    assert ApiSettings().secure_cookies is False
    assert (
        ApiSettings(
            environment=Environment.PRODUCTION,
            allowed_origins=("https://app.example.com",),
        ).secure_cookies
        is True
    )


def test_environment_loader_rejects_unknown_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LMS_ENVIRONMENT", "somewhere")

    with pytest.raises(ApiConfigurationError, match="LMS_ENVIRONMENT must be one of"):
        ApiSettings.from_environment()


def test_environment_loader_rejects_invalid_security_integer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LMS_LOGIN_RATE_LIMIT", "many")

    with pytest.raises(ApiConfigurationError, match="LMS_LOGIN_RATE_LIMIT must be an integer"):
        ApiSettings.from_environment()


def test_cookie_names_must_be_distinct_safe_tokens() -> None:
    with pytest.raises(ApiConfigurationError, match="distinct tokens"):
        ApiSettings(session_cookie_name="same", csrf_cookie_name="same")
