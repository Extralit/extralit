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


from fastapi import Request
from fastapi.security import APIKeyHeader
from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.contexts import accounts
from extralit_server.security.authentication.userinfo import UserInfo


class APIKeyAuthenticationBackend(AuthenticationBackend):
    """Authentication backend for API Key authentication"""

    scheme = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)

    async def authenticate(self, request: Request) -> tuple[AuthCredentials, BaseUser] | None:
        """Authenticate the user using the API Key header"""
        api_key: str = await self.scheme(request)
        if not api_key:
            return None

        db = request.state.db
        user = await accounts.get_user_by_api_key(db, api_key=api_key)
        if not user:
            return None

        return AuthCredentials(), UserInfo(
            username=user.username, name=user.first_name, role=user.role, identity=str(user.id)
        )
