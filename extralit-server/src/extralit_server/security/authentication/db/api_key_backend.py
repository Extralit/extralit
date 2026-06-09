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
