"""Shared authorization checks for application services."""

from collections.abc import Collection

from library_management.domain import User, UserRole
from library_management.repositories import UnitOfWork
from library_management.services.errors import AuthorizationError


def require_active_user(unit_of_work: UnitOfWork, user_id: int) -> User:
    user = unit_of_work.users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise AuthorizationError("An active account is required.")
    return user


def require_role(
    unit_of_work: UnitOfWork,
    user_id: int,
    allowed_roles: Collection[UserRole],
    message: str,
) -> User:
    user = require_active_user(unit_of_work, user_id)
    if user.role not in allowed_roles:
        raise AuthorizationError(message)
    return user
