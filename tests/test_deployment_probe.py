import pytest

from scripts.deployment_probe import parse_server_timing, summarize, validate_origin


def test_hosted_probe_requires_a_credential_free_https_origin() -> None:
    assert validate_origin("https://api.staging.example") == "https://api.staging.example"
    with pytest.raises(ValueError, match="HTTPS"):
        validate_origin("http://api.staging.example")
    with pytest.raises(ValueError, match="credential-free"):
        validate_origin("https://user:secret@api.staging.example")
    with pytest.raises(ValueError, match="Origins"):
        validate_origin("https://api.staging.example/path")


def test_probe_permits_explicit_loopback_http_for_local_rehearsal() -> None:
    assert validate_origin("http://127.0.0.1:8000") == "http://127.0.0.1:8000"


def test_latency_summary_uses_nearest_rank_p95() -> None:
    result = summarize([float(value) for value in range(1, 21)])

    assert result == {
        "minimum_ms": 1.0,
        "median_ms": 10.5,
        "p95_ms": 19.0,
        "maximum_ms": 20.0,
    }


def test_server_timing_parser_separates_application_and_database_spans() -> None:
    value = "app;dur=12.45, db;dur=3.20"

    assert parse_server_timing(value, "app") == 12.45
    assert parse_server_timing(value, "db") == 3.2
    assert parse_server_timing(value, "missing") is None
