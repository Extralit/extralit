import os
from typing import Any

from starlette.authentication import BaseUser

from extralit_server.enums import UserRole

_DEFAULT_USER_ROLE = UserRole.annotator


class UserInfo(BaseUser, dict):
    """User info from a provider."""

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def username(self) -> str:
        return self.get("username", "")

    @property
    def first_name(self) -> str:
        return self.get("first_name") or self.username

    @property
    def last_name(self) -> str | None:
        return self.get("last_name") or None

    @property
    def role(self) -> UserRole:
        role = self.get("role") or self._parse_role_from_environment()
        return UserRole(role)

    @property
    def available_workspaces(self) -> list | None:
        return self.get("available_workspaces")

    def _parse_role_from_environment(self) -> UserRole | None:
        """This is a temporal solution, and it will be replaced by a proper Sign up process"""
        if self.get("username") == os.getenv("USERNAME"):
            return UserRole.owner
        return _DEFAULT_USER_ROLE

    def __getprop__(self, item, default="") -> Any:
        if callable(item):
            return item(self)
        return self.get(item, default)

    __getattr__ = __getprop__
