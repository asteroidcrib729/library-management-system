"""Account creation, authentication, and authorization use cases."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from library_management.domain import User, UserRole
from library_management.repositories import DuplicateRecordError, UnitOfWork
from library_management.security import PasswordService
from library_management.services.authorization import require_active_user, require_role
from library_management.services.errors import (
    AuthenticationError,
    AuthorizationError,
    BootstrapClosedError,
    LastAdministratorError,
    PasswordPolicyError,
    UsernameUnavailableError,
)

UnitOfWorkFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Account details safe to expose to presentation code."""

    user_id: int
    display_name: str
    username: str
    role: UserRole

    @classmethod
    def from_user(cls, user: User) -> AuthenticatedPrincipal:
        if user.id is None:
            raise ValueError("An authenticated user must have a persistent identifier.")
        return cls(
            user_id=user.id,
            display_name=user.display_name,
            username=user.username,
            role=user.role,
        )


class PasswordPolicy:
    """Length-based password policy suitable for passphrases."""

    minimum_length = 12
    maximum_length = 128

    def validate(self, password: str) -> None:
        if len(password) < self.minimum_length:
            raise PasswordPolicyError(
                f"Password must contain at least {self.minimum_length} characters."
            )
        if len(password) > self.maximum_length:
            raise PasswordPolicyError(
                f"Password must contain no more than {self.maximum_length} characters."
            )
        if not password.strip():
            raise PasswordPolicyError("Password cannot consist only of whitespace.")


class AccountService:
    """Create and deactivate accounts under explicit authorization rules."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        password_service: PasswordService,
        password_policy: PasswordPolicy | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._password_service = password_service
        self._password_policy = password_policy or PasswordPolicy()

    def register_member(
        self, display_name: str, username: str, password: str
    ) -> AuthenticatedPrincipal:
        return self._create_account(display_name, username, password, UserRole.MEMBER)

    def bootstrap_administrator(
        self, display_name: str, username: str, password: str
    ) -> AuthenticatedPrincipal:
        self._password_policy.validate(password)
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.lock_bootstrap()
            if unit_of_work.users.count_by_role(UserRole.ADMINISTRATOR) > 0:
                raise BootstrapClosedError("Administrator bootstrap has already been completed.")
            administrator = self._build_user(
                display_name, username, password, UserRole.ADMINISTRATOR
            )
            try:
                saved = unit_of_work.users.add(administrator)
            except DuplicateRecordError as error:
                raise UsernameUnavailableError("That username is not available.") from error
            unit_of_work.commit()
        return AuthenticatedPrincipal.from_user(saved)

    def create_librarian(
        self,
        actor_id: int,
        display_name: str,
        username: str,
        password: str,
    ) -> AuthenticatedPrincipal:
        self._password_policy.validate(password)
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.lock_rows(users=(actor_id,))
            require_role(
                unit_of_work,
                actor_id,
                {UserRole.ADMINISTRATOR},
                "Administrator permission is required.",
            )
            librarian = self._build_user(display_name, username, password, UserRole.LIBRARIAN)
            saved = self._add_user(unit_of_work, librarian)
            unit_of_work.commit()
        return AuthenticatedPrincipal.from_user(saved)

    def deactivate_account(self, actor_id: int, target_username: str) -> AuthenticatedPrincipal:
        with self._unit_of_work_factory() as unit_of_work:
            target = unit_of_work.users.get_by_username(target_username)
            if target is None or not target.is_active:
                raise AuthenticationError("The requested active account was not found.")
            if target.id is None:
                raise RuntimeError("A stored user is missing its identifier.")
            unit_of_work.lock_rows(users=(actor_id, target.id))
            actor = require_active_user(unit_of_work, actor_id)
            target = unit_of_work.users.get_by_id(target.id)
            if target is None or not target.is_active or target.id is None:
                raise AuthenticationError("The requested active account was not found.")
            if actor.id != target.id and actor.role is not UserRole.ADMINISTRATOR:
                raise AuthorizationError("Administrator permission is required.")
            if (
                target.role is UserRole.ADMINISTRATOR
                and unit_of_work.users.count_active_by_role(UserRole.ADMINISTRATOR) <= 1
            ):
                raise LastAdministratorError(
                    "The final active administrator cannot be deactivated."
                )
            unit_of_work.users.deactivate(target.id)
            unit_of_work.commit()
        return AuthenticatedPrincipal.from_user(target)

    def _create_account(
        self,
        display_name: str,
        username: str,
        password: str,
        role: UserRole,
    ) -> AuthenticatedPrincipal:
        self._password_policy.validate(password)
        user = self._build_user(display_name, username, password, role)
        with self._unit_of_work_factory() as unit_of_work:
            saved = self._add_user(unit_of_work, user)
            unit_of_work.commit()
        return AuthenticatedPrincipal.from_user(saved)

    @staticmethod
    def _add_user(unit_of_work: UnitOfWork, user: User) -> User:
        try:
            return unit_of_work.users.add(user)
        except DuplicateRecordError as error:
            raise UsernameUnavailableError("That username is not available.") from error

    def _build_user(
        self,
        display_name: str,
        username: str,
        password: str,
        role: UserRole,
    ) -> User:
        return User(
            display_name=display_name,
            username=username,
            password_hash=self._password_service.hash(password),
            role=role,
        )


class AuthenticationService:
    """Authenticate accounts without leaking account existence or hash details."""

    _failure_message = "Invalid username or password."

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        password_service: PasswordService,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._password_service = password_service
        self._dummy_hash = password_service.hash("dummy-password-never-used")

    def authenticate(self, username: str, password: str) -> AuthenticatedPrincipal:
        with self._unit_of_work_factory() as unit_of_work:
            user = unit_of_work.users.get_by_username(username)
            encoded_hash = user.password_hash if user is not None else self._dummy_hash
            verification = self._password_service.verify(password, encoded_hash)

            if user is None or not user.is_active or not verification.verified:
                raise AuthenticationError(self._failure_message)

            if verification.replacement_hash is not None:
                if user.id is None:
                    raise RuntimeError("A stored user is missing its identifier.")
                unit_of_work.users.update_password_hash(user.id, verification.replacement_hash)
                unit_of_work.commit()

        return AuthenticatedPrincipal.from_user(user)
