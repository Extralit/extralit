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

from typing import ClassVar

from fastapi import Depends
from fastapi.security import SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.authentication import AuthenticationBackend
from starlette.requests import Request

from extralit_server.contexts import accounts
from extralit_server.database import get_async_db
from extralit_server.errors import UnauthorizedError
from extralit_server.models import User
from extralit_server.security.authentication.db import APIKeyAuthenticationBackend, BearerTokenAuthenticationBackend
from extralit_server.security.authentication.userinfo import UserInfo


def set_request_user(request: Request, user: User):
    """
    Set the request user in the request state.

    Parameters:
        request: The request object.
        user: The user.

    """

    request.state.user = user


def get_request_user(request: Request) -> User | None:
    """
    Get the current user from the request.

    Parameters:
        request (Request): The request object.

    Returns:
        The user if available, None otherwise.
    """
    return getattr(request.state, "user", None)


class AuthenticationProvider:
    """Authentication provider for the API requests."""

    backends: ClassVar[list[AuthenticationBackend]] = [
        APIKeyAuthenticationBackend(),
        BearerTokenAuthenticationBackend(),
    ]

    @classmethod
    def new_instance(cls):
        return AuthenticationProvider()

    async def get_current_user(
        self,
        security_scopes: SecurityScopes,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        _api_key: str | None = Depends(APIKeyAuthenticationBackend.scheme),
        _bearer: str | None = Depends(BearerTokenAuthenticationBackend.scheme),
    ) -> User:
        """Get the current user from the request."""

        userinfo = await self._authenticate_request_user(db, request)
        if not userinfo:
            raise UnauthorizedError()

        user = await accounts.get_user_by_username(db, userinfo.username)
        if not user:
            raise UnauthorizedError()

        set_request_user(request, user)
        return user

    async def get_optional_current_user(
        self,
        security_scopes: SecurityScopes,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        _api_key: str | None = Depends(APIKeyAuthenticationBackend.scheme),
        _bearer: str | None = Depends(BearerTokenAuthenticationBackend.scheme),
    ) -> User | None:
        """Get the current user from the request, or None if authentication fails."""

        userinfo = await self._authenticate_request_user(db, request)
        if not userinfo:
            return None

        user = await accounts.get_user_by_username(db, userinfo.username)
        if not user:
            return None

        return user

    async def _authenticate_request_user(self, db: AsyncSession, request: Request) -> UserInfo | None:
        # This db will be used by the backends. Ideally this should be done as a global dependency
        # but is not working as expected. Sometimes the db is not available in the request state at the
        # middlewares level.
        request.state.db = db

        for backend in self.backends:
            if results := await backend.authenticate(request):
                _, userinfo = results
                return userinfo

        return None
