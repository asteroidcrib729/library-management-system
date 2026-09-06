"""Atomic idempotent command execution over the existing service layer."""

from __future__ import annotations

import hashlib
import json
import random
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder

from library_management.postgres import PostgresDatabase
from library_management.postgres.database import RetryableTransactionError
from library_management.repositories.postgres.idempotency import IdempotencyDecision
from library_management.repositories.postgres.unit_of_work import (
    BorrowedPostgresUnitOfWork,
    PostgresUnitOfWork,
)


def idempotency_key(request: Request) -> str:
    value = request.headers.get("Idempotency-Key", "").strip()
    if not 8 <= len(value) <= 200:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Idempotency-Key must contain between 8 and 200 characters.",
        )
    return value


def execute_idempotent[T](
    *,
    database: PostgresDatabase,
    actor_id: int,
    operation: str,
    key: str,
    request_body: Any,
    command: Callable[[BorrowedPostgresUnitOfWork], T],
    response_model: type[Any],
    response_status: int = status.HTTP_200_OK,
) -> tuple[T | dict[str, Any], int, bool]:
    canonical = json.dumps(jsonable_encoder(request_body), sort_keys=True, separators=(",", ":"))
    request_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    for attempt in range(3):
        try:
            with PostgresUnitOfWork(database) as outer:
                now = datetime.now(UTC)
                owner_token = secrets.token_urlsafe(24)
                decision = outer.idempotency.claim(
                    actor_id=actor_id,
                    operation=operation,
                    key=key,
                    request_hash=request_hash,
                    owner_token=owner_token,
                    now=now,
                    expires_at=now + timedelta(minutes=2),
                )
                if decision.decision is IdempotencyDecision.IN_PROGRESS:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        "An equivalent command is already in progress.",
                        headers={"Retry-After": "2"},
                    )
                if decision.decision is IdempotencyDecision.REPLAY:
                    if decision.response is None or decision.response_status is None:
                        raise RuntimeError("Stored idempotency response is incomplete.")
                    return decision.response, decision.response_status, True
                result = command(outer.borrowed())
                payload = response_model.model_validate(result).model_dump(
                    mode="json", by_alias=True
                )
                outer.idempotency.complete(
                    actor_id=actor_id,
                    operation=operation,
                    key=key,
                    owner_token=owner_token,
                    response=payload,
                    response_status=response_status,
                    expires_at=now + timedelta(hours=24),
                )
                outer.commit()
                return result, response_status, False
        except RetryableTransactionError:
            if attempt == 2:
                raise
            time.sleep(0.02 * (2**attempt) + random.uniform(0, 0.02))
    raise AssertionError("Unreachable retry state.")
