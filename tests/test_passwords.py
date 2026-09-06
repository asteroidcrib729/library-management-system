import pytest

from library_management.security import PasswordService


def test_password_hash_can_be_verified_without_storing_plaintext() -> None:
    service = PasswordService()
    password = "correct horse battery staple"

    encoded_hash = service.hash(password)
    result = service.verify(password, encoded_hash)

    assert result.verified is True
    assert result.replacement_hash is None
    assert password not in encoded_hash
    assert encoded_hash.startswith("$argon2id$")


def test_incorrect_password_is_rejected() -> None:
    service = PasswordService()
    encoded_hash = service.hash("correct password")

    result = service.verify("incorrect password", encoded_hash)

    assert result.verified is False
    assert result.replacement_hash is None


def test_invalid_hash_is_rejected() -> None:
    result = PasswordService().verify("password", "not-an-argon2-hash")

    assert result.verified is False


def test_empty_password_cannot_be_hashed() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        PasswordService().hash("")
