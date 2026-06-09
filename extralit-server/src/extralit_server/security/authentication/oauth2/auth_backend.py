from fastapi import Request
from fastapi.security import HTTPBearer
from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser

from extralit_server.security.authentication.jwt import JWT
from extralit_server.security.authentication.oauth2.provider import OAuth2ClientProvider
from extralit_server.security.authentication.userinfo import UserInfo


class OAuth2AuthenticationBackend(AuthenticationBackend):
    """Authentication backend for AuthenticationMiddleware."""

    scheme = HTTPBearer(auto_error=False)

    def __init__(self, providers: dict[str, OAuth2ClientProvider]) -> None:
        self.providers = providers

    async def authenticate(self, request: Request) -> tuple[AuthCredentials, BaseUser] | None:
        credentials = await self.scheme(request)
        if credentials is None:
            return None

        token_data = JWT.decode(credentials.credentials)
        user = UserInfo(token_data)

        return AuthCredentials(user.pop("scope", [])), user
