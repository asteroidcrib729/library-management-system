"""Credential-safe smoke and latency probes for an isolated LMS deployment."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from http.client import HTTPMessage
from http.cookiejar import CookieJar
from pathlib import Path
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Observation:
    name: str
    status: int
    elapsed_ms: float
    response_bytes: int
    request_id_present: bool
    server_timing: str | None


class ProbeFailure(RuntimeError):
    """A deployment violated a required observable contract."""


def validate_origin(value: str) -> str:
    """Accept an HTTPS origin, or HTTP only for an explicit loopback target."""

    parsed = urlsplit(value)
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if (
        parsed.scheme not in ({"http", "https"} if local else {"https"})
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Origins must be credential-free HTTPS origins (HTTP is loopback-only).")
    return f"{parsed.scheme}://{parsed.netloc}"


def summarize(values: Sequence[float]) -> dict[str, float]:
    """Return deterministic nearest-rank latency statistics."""

    if not values:
        raise ValueError("At least one measurement is required.")
    ordered = sorted(values)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "minimum_ms": round(ordered[0], 2),
        "median_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(ordered[p95_index], 2),
        "maximum_ms": round(ordered[-1], 2),
    }


def parse_server_timing(value: str | None, metric: str) -> float | None:
    """Read one duration from the small Server-Timing contract without trusting labels."""

    if not value:
        return None
    for item in value.split(","):
        fields = [field.strip() for field in item.split(";")]
        if fields[0] != metric:
            continue
        duration = next((field[4:] for field in fields[1:] if field.startswith("dur=")), None)
        if duration is None:
            return None
        try:
            return float(duration)
        except ValueError:
            return None
    return None


class DeploymentClient:
    def __init__(self, timeout_seconds: float) -> None:
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        name: str,
        url: str,
        *,
        method: str = "GET",
        headers: Mapping[str, str] | None = None,
        body: Mapping[str, object] | None = None,
    ) -> tuple[Observation, bytes, HTTPMessage]:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request_headers = {"Accept": "application/json", **(headers or {})}
        if payload is not None:
            request_headers["Content-Type"] = "application/json"
        request = Request(url, data=payload, headers=request_headers, method=method)
        started = time.perf_counter()
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                content = cast(bytes, response.read())
                status = response.status
                response_headers = cast(HTTPMessage, response.headers)
        except HTTPError as error:
            content = cast(bytes, error.read())
            status = error.code
            response_headers = cast(HTTPMessage, error.headers)
        except (TimeoutError, URLError) as error:
            raise ProbeFailure(
                f"{name} could not reach its target: {type(error).__name__}"
            ) from error
        elapsed_ms = (time.perf_counter() - started) * 1000
        observation = Observation(
            name=name,
            status=status,
            elapsed_ms=round(elapsed_ms, 2),
            response_bytes=len(content),
            request_id_present=bool(response_headers.get("X-Request-ID")),
            server_timing=response_headers.get("Server-Timing"),
        )
        return observation, content, response_headers


def run_smoke(args: argparse.Namespace) -> dict[str, object]:
    api_origin = validate_origin(args.api_origin)
    web_origin = validate_origin(args.web_origin)
    client = DeploymentClient(args.timeout)
    observations: list[Observation] = []

    web, _, web_headers = client.request("web_root", f"{web_origin}/")
    _require_status(web, 200)
    observations.append(web)
    for header in ("X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"):
        if not web_headers.get(header):
            raise ProbeFailure(f"Web response is missing {header}.")

    for name, path in (("api_live", "/health/live"), ("api_ready", "/health/ready")):
        observation, _, headers = client.request(
            name,
            f"{api_origin}{path}",
            headers={"Origin": web_origin},
        )
        _require_status(observation, 200)
        if headers.get("Access-Control-Allow-Origin") != web_origin:
            raise ProbeFailure(f"{name} did not allow the exact dashboard origin.")
        if not observation.server_timing:
            raise ProbeFailure(f"{name} did not expose Server-Timing.")
        observations.append(observation)

    preflight, _, preflight_headers = client.request(
        "cors_preflight",
        f"{api_origin}/api/v1/auth/logout",
        method="OPTIONS",
        headers={
            "Origin": web_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-CSRF-Token",
        },
    )
    _require_status(preflight, 200)
    if preflight_headers.get("Access-Control-Allow-Origin") != web_origin:
        raise ProbeFailure("Credentialed CORS preflight did not echo the exact origin.")
    observations.append(preflight)

    rejected, _, _ = client.request(
        "untrusted_origin",
        f"{api_origin}/api/v1/auth/logout",
        method="POST",
        headers={"Origin": "https://untrusted.invalid"},
    )
    _require_status(rejected, 403)
    observations.append(rejected)

    authenticated = False
    username = _environment_value(args.username_environment)
    password = _environment_value(args.password_environment)
    if bool(username) != bool(password):
        raise ProbeFailure("Both synthetic smoke credential environment variables are required.")
    if username and password:
        authenticated = True
        login, _, login_headers = client.request(
            "login",
            f"{api_origin}/api/v1/auth/login",
            method="POST",
            headers={"Origin": web_origin},
            body={"username": username, "password": password},
        )
        _require_status(login, 200)
        _verify_cookie_headers(login_headers, args.session_cookie, args.csrf_cookie)
        observations.append(login)

        current, _, _ = client.request(
            "current_session",
            f"{api_origin}/api/v1/auth/session",
            headers={"Origin": web_origin},
        )
        _require_status(current, 200)
        observations.append(current)
        csrf = next(
            (cookie.value for cookie in client.cookies if cookie.name == args.csrf_cookie), None
        )
        if not csrf:
            raise ProbeFailure("Readable CSRF cookie was not issued.")
        logout, _, _ = client.request(
            "logout",
            f"{api_origin}/api/v1/auth/logout",
            method="POST",
            headers={"Origin": web_origin, "X-CSRF-Token": csrf},
        )
        _require_status(logout, 200)
        observations.append(logout)

    return {
        "kind": "smoke",
        "authenticated_session_checked": authenticated,
        "observations": [asdict(item) for item in observations],
    }


def run_measure(args: argparse.Namespace) -> dict[str, object]:
    api_origin = validate_origin(args.api_origin)
    web_origin = validate_origin(args.web_origin)
    client = DeploymentClient(args.timeout)
    series: dict[str, list[Observation]] = {"web_root": [], "api_ready": []}
    for _ in range(args.samples):
        web, _, _ = client.request("web_root", f"{web_origin}/")
        ready, _, _ = client.request(
            "api_ready", f"{api_origin}/health/ready", headers={"Origin": web_origin}
        )
        _require_status(web, 200)
        _require_status(ready, 200)
        series["web_root"].append(web)
        series["api_ready"].append(ready)
    return {
        "kind": "measurement",
        "samples": args.samples,
        "targets": {
            name: {
                **summarize([item.elapsed_ms for item in observations]),
                "mean_response_bytes": round(
                    statistics.mean(item.response_bytes for item in observations), 2
                ),
                "server_timing_present": all(item.server_timing for item in observations),
                "mean_server_app_ms": _mean_timing(observations, "app"),
                "mean_server_db_probe_ms": _mean_timing(observations, "db"),
            }
            for name, observations in series.items()
        },
    }


def run_load(args: argparse.Namespace) -> dict[str, object]:
    """Run an explicitly authorized synthetic authenticated workload."""

    api_origin = validate_origin(args.api_origin)
    web_origin = validate_origin(args.web_origin)
    password = _environment_value(args.password_environment)
    if not password:
        raise ProbeFailure("The synthetic load password environment variable is required.")
    clients: list[tuple[DeploymentClient, str]] = []
    for index in range(1, args.users + 1):
        client = DeploymentClient(args.timeout)
        username = f"{args.username_prefix}{index:02d}"
        login, _, _ = client.request(
            "login",
            f"{api_origin}/api/v1/auth/login",
            method="POST",
            headers={"Origin": web_origin},
            body={"username": username, "password": password},
        )
        _require_status(login, 200)
        csrf = next(
            (cookie.value for cookie in client.cookies if cookie.name == args.csrf_cookie), None
        )
        if not csrf:
            raise ProbeFailure(f"Synthetic user {index} did not receive a CSRF cookie.")
        clients.append((client, csrf))

    started = time.monotonic()
    deadline = started + args.duration_seconds
    recorded: list[tuple[str, int, float]] = []
    record_lock = threading.Lock()
    reads = (
        "/api/v1/catalog/books?limit=20",
        "/api/v1/circulation/loans?limit=20",
        "/api/v1/circulation/reservations?limit=20",
        "/api/v1/finance/fines?limit=20",
    )

    def worker(worker_index: int, client: DeploymentClient, csrf: str) -> None:
        sequence = 0
        while time.monotonic() < deadline:
            is_write = args.write_every > 0 and sequence % args.write_every == 0
            if is_write:
                operation = "feedback_write"
                observation, _, _ = client.request(
                    operation,
                    f"{api_origin}/api/v1/engagement/feedback",
                    method="POST",
                    headers={
                        "Origin": web_origin,
                        "X-CSRF-Token": csrf,
                        "Idempotency-Key": str(uuid4()),
                    },
                    body={"content": f"Synthetic Plan 18 load record {worker_index}-{sequence}"},
                )
            else:
                operation = "authenticated_read"
                path = reads[sequence % len(reads)]
                observation, _, _ = client.request(
                    operation,
                    f"{api_origin}{path}",
                    headers={"Origin": web_origin},
                )
            with record_lock:
                recorded.append((operation, observation.status, observation.elapsed_ms))
            sequence += 1
            if args.think_time > 0:
                time.sleep(args.think_time)

    with ThreadPoolExecutor(max_workers=args.users) as executor:
        futures = [
            executor.submit(worker, index, client, csrf)
            for index, (client, csrf) in enumerate(clients, start=1)
        ]
        for future in futures:
            future.result()

    accepted_statuses = {200, 201, 429, 503}
    unexpected = sum(status not in accepted_statuses for _, status, _ in recorded)
    operations: dict[str, object] = {}
    for operation in ("authenticated_read", "feedback_write"):
        selected = [(status, elapsed) for name, status, elapsed in recorded if name == operation]
        if not selected:
            continue
        status_counts: dict[str, int] = {}
        for status, _ in selected:
            status_counts[str(status)] = status_counts.get(str(status), 0) + 1
        operations[operation] = {
            **summarize([elapsed for _, elapsed in selected]),
            "requests": len(selected),
            "status_counts": status_counts,
        }
    return {
        "kind": "synthetic_load",
        "users": args.users,
        "duration_seconds": round(time.monotonic() - started, 2),
        "write_every": args.write_every,
        "operations": operations,
        "unexpected_statuses": unexpected,
        "passed": unexpected == 0,
    }


def _mean_timing(observations: Sequence[Observation], metric: str) -> float | None:
    values = [
        value
        for observation in observations
        if (value := parse_server_timing(observation.server_timing, metric)) is not None
    ]
    return round(statistics.mean(values), 2) if values else None


def _environment_value(name: str | None) -> str | None:
    if not name:
        return None
    value = os.environ.get(name)
    return value if value else None


def _require_status(observation: Observation, expected: int) -> None:
    if observation.status != expected:
        raise ProbeFailure(
            f"{observation.name} returned HTTP {observation.status}; expected {expected}."
        )


def _verify_cookie_headers(headers: HTTPMessage, session_cookie: str, csrf_cookie: str) -> None:
    values: list[str] = headers.get_all("Set-Cookie", [])
    session = next((value for value in values if value.startswith(f"{session_cookie}=")), "")
    csrf = next((value for value in values if value.startswith(f"{csrf_cookie}=")), "")
    required = ("secure", "samesite=lax")
    if not session or not all(item in session.lower() for item in (*required, "httponly")):
        raise ProbeFailure("Session cookie is missing Secure, HttpOnly, or SameSite=Lax.")
    if not csrf or not all(item in csrf.lower() for item in required) or "httponly" in csrf.lower():
        raise ProbeFailure("CSRF cookie transport flags do not match the browser contract.")


def _write_result(result: dict[str, object], output: Path | None) -> None:
    serialized = json.dumps(result, indent=2, sort_keys=True)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(f"{serialized}\n", encoding="utf-8")
    else:
        print(serialized)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("smoke", "measure"):
        command = subparsers.add_parser(name)
        command.add_argument("--api-origin", required=True)
        command.add_argument("--web-origin", required=True)
        command.add_argument("--timeout", type=float, default=20.0)
        command.add_argument("--output", type=Path)
        if name == "smoke":
            command.add_argument("--username-environment")
            command.add_argument("--password-environment")
            command.add_argument("--session-cookie", default="lms_session")
            command.add_argument("--csrf-cookie", default="lms_csrf")
        else:
            command.add_argument("--samples", type=int, choices=range(5, 201), default=25)
    load = subparsers.add_parser("load")
    load.add_argument("--api-origin", required=True)
    load.add_argument("--web-origin", required=True)
    load.add_argument("--password-environment", required=True)
    load.add_argument("--username-prefix", default="load.user.")
    load.add_argument("--csrf-cookie", default="lms_csrf")
    load.add_argument("--users", type=int, choices=range(1, 51), default=20)
    load.add_argument("--duration-seconds", type=int, choices=range(10, 1801), default=1800)
    load.add_argument("--write-every", type=int, choices=range(0, 101), default=20)
    load.add_argument("--think-time", type=float, default=1.0)
    load.add_argument("--timeout", type=float, default=20.0)
    load.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "smoke":
            result = run_smoke(args)
        elif args.command == "measure":
            result = run_measure(args)
        else:
            result = run_load(args)
        _write_result(result, args.output)
        return 0 if result.get("passed", True) else 1
    except (ProbeFailure, ValueError) as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
