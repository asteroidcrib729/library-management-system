"""Secure password hashing and verification."""

from __future__ import annotations

from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """The outcome of password verification and an optional upgraded hash."""

    verified: bool
    replacement_hash: str | None = None


class PasswordService:
    """Hash passwords with Argon2id and upgrade old hashes after login."""

    def __init__(self, hasher: PasswordHasher | None = None) -> None:
        self._hasher = hasher or PasswordHasher()

    def hash(self, password: str) -> str:
        """Return an encoded Argon2id hash using a random salt."""
        if not password:
            raise ValueError("Password must not be empty.")
        return self._hasher.hash(password)

    def verify(self, password: str, encoded_hash: str) -> VerificationResult:
        """Verify a password and provide a replacement for outdated hashes."""
        try:
            self._hasher.verify(encoded_hash, password)
        except InvalidHashError, VerificationError:
            return VerificationResult(verified=False)

        replacement_hash = (
            self._hasher.hash(password) if self._hasher.check_needs_rehash(encoded_hash) else None
        )
        return VerificationResult(verified=True, replacement_hash=replacement_hash)
