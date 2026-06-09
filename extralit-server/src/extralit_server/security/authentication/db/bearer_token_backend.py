from fastapi import Request
from fastapi.security import HTTPBearer
from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser

from extralit_server.contexts import accounts
from extralit_server.security.authentication.jwt import JWT
from extralit_server.security.authentication.userinfo import UserInfo


class BearerTokenAuthenticationBackend(AuthenticationBackend):
    """Authenticate the user using the username and password Bearer header"""

    scheme = HTTPBearer(auto_error=False)

    async def authenticate(self, request: Request) -> tuple[AuthCredentials, BaseUser] | None:
        """Authenticate the user using the username and password Bearer header"""
        credentials = await self.scheme(request)
        if not credentials:
            return None

        token = credentials.credentials
        username = JWT.decode(token).get("username")

        db = request.state.db
        user = await accounts.get_user_by_username(db, username)
        if not user:
            return None

        return AuthCredentials(), UserInfo(
            username=user.username, name=user.first_name, role=user.role, identity=str(user.id)
        )
