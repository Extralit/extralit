# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
        return self["username"]

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
        if self["username"] == os.getenv("USERNAME"):
            return UserRole.owner
        return _DEFAULT_USER_ROLE

    def __getprop__(self, item, default="") -> Any:
        if callable(item):
            return item(self)
        return self.get(item, default)

    __getattr__ = __getprop__
