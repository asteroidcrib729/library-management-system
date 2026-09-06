from collections.abc import Callable
from functools import partial

import pytest
from argon2 import PasswordHasher

from library_management.database import Database
from library_management.domain import User, UserRole
from library_management.repositories import UnitOfWork
from library_management.repositories.sqlite import SqliteUnitOfWork
from library_management.security import PasswordService
from library_management.services import (
    AccountService,
    AuthenticationError,
    AuthenticationService,
    AuthorizationError,
    BootstrapClosedError,
    LastAdministratorError,
    PasswordPolicyError,
    UsernameUnavailableError,
)


def build_services(
    database: Database,
) -> tuple[AccountService, AuthenticationService, Callable[[], UnitOfWork]]:
    factory: Callable[[], UnitOfWork] = partial(SqliteUnitOfWork, database)
    password_service = PasswordService()
    return (
        AccountService(factory, password_service),
        AuthenticationService(factory, password_service),
        factory,
    )


def test_member_registration_hashes_password_and_authenticates(database: Database) -> None:
    accounts, authentication, factory = build_services(database)
    password = "a long library passphrase"

    principal = accounts.register_member("Reader One", "Reader.One", password)

    with factory() as unit_of_work:
        stored = unit_of_work.users.get_by_username("reader.one")

    assert principal.role is UserRole.MEMBER
    assert stored is not None
    assert stored.password_hash != password
    assert stored.password_hash.startswith("$argon2id$")
    assert authentication.authenticate("READER.ONE", password) == principal


@pytest.mark.parametrize("password", ["short", " " * 12, "x" * 129])
def test_registration_enforces_password_policy(database: Database, password: str) -> None:
    accounts, _, _ = build_services(database)

    with pytest.raises(PasswordPolicyError):
        accounts.register_member("Reader", "reader.one", password)


def test_duplicate_username_has_safe_registration_error(database: Database) -> None:
    accounts, _, _ = build_services(database)
    accounts.register_member("First Reader", "reader.one", "first long password")

    with pytest.raises(UsernameUnavailableError, match="not available"):
        accounts.register_member("Second Reader", "READER.ONE", "second long password")


def test_administrator_bootstrap_can_only_run_once(database: Database) -> None:
    accounts, _, _ = build_services(database)

    administrator = accounts.bootstrap_administrator(
        "System Admin", "admin", "administrator passphrase"
    )

    assert administrator.role is UserRole.ADMINISTRATOR
    with pytest.raises(BootstrapClosedError):
        accounts.bootstrap_administrator("Other Admin", "admin.two", "another passphrase")


def test_only_administrator_can_create_librarian(database: Database) -> None:
    accounts, _, _ = build_services(database)
    member = accounts.register_member("Reader", "reader.one", "member passphrase")

    with pytest.raises(AuthorizationError, match="Administrator"):
        accounts.create_librarian(
            member.user_id,
            "Librarian",
            "librarian.one",
            "librarian passphrase",
        )

    administrator = accounts.bootstrap_administrator(
        "Administrator", "admin", "administrator passphrase"
    )
    librarian = accounts.create_librarian(
        administrator.user_id,
        "Librarian",
        "librarian.one",
        "librarian passphrase",
    )

    assert librarian.role is UserRole.LIBRARIAN


def test_authentication_uses_same_error_for_wrong_unknown_and_inactive_accounts(
    database: Database,
) -> None:
    accounts, authentication, _ = build_services(database)
    member = accounts.register_member("Reader", "reader.one", "member passphrase")

    with pytest.raises(AuthenticationError) as wrong_password:
        authentication.authenticate("reader.one", "wrong passphrase")
    with pytest.raises(AuthenticationError) as unknown_user:
        authentication.authenticate("unknown.user", "wrong passphrase")

    accounts.deactivate_account(member.user_id, member.username)
    with pytest.raises(AuthenticationError) as inactive_user:
        authentication.authenticate("reader.one", "member passphrase")

    assert str(wrong_password.value) == str(unknown_user.value) == str(inactive_user.value)


def test_member_cannot_deactivate_another_account(database: Database) -> None:
    accounts, _, _ = build_services(database)
    first = accounts.register_member("First", "reader.one", "first long password")
    accounts.register_member("Second", "reader.two", "second long password")

    with pytest.raises(AuthorizationError, match="Administrator"):
        accounts.deactivate_account(first.user_id, "reader.two")


def test_administrator_can_deactivate_another_account(database: Database) -> None:
    accounts, authentication, _ = build_services(database)
    administrator = accounts.bootstrap_administrator(
        "Administrator", "admin", "administrator passphrase"
    )
    accounts.register_member("Reader", "reader.one", "member passphrase")

    deactivated = accounts.deactivate_account(administrator.user_id, "reader.one")

    assert deactivated.username == "reader.one"
    with pytest.raises(AuthenticationError):
        authentication.authenticate("reader.one", "member passphrase")


def test_final_active_administrator_cannot_be_deactivated(database: Database) -> None:
    accounts, _, _ = build_services(database)
    administrator = accounts.bootstrap_administrator(
        "Administrator", "admin", "administrator passphrase"
    )

    with pytest.raises(LastAdministratorError, match="final active"):
        accounts.deactivate_account(administrator.user_id, administrator.username)


def test_authentication_upgrades_outdated_hash(database: Database) -> None:
    factory: Callable[[], UnitOfWork] = partial(SqliteUnitOfWork, database)
    old_password_service = PasswordService(
        PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    )
    password = "upgrade this passphrase"
    old_hash = old_password_service.hash(password)

    with factory() as unit_of_work:
        saved = unit_of_work.users.add(
            User(
                display_name="Reader",
                username="reader.one",
                password_hash=old_hash,
            )
        )
        unit_of_work.commit()

    authentication = AuthenticationService(factory, PasswordService())
    authentication.authenticate(saved.username, password)

    with factory() as unit_of_work:
        updated = unit_of_work.users.get_by_id(saved.id or 0)

    assert updated is not None
    assert updated.password_hash != old_hash
    assert PasswordService().verify(password, updated.password_hash).verified is True
