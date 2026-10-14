from datetime import datetime, timedelta
from typing import Literal

from jose import JWTError, jwt

from extralit_server.errors import UnauthorizedError
from extralit_server.security.authentication.userinfo import UserInfo
from extralit_server.security.settings import settings

TokenType = Literal["access", "refresh"]


class JWT:
    secret: str = settings.secret_key
    algorithm: str = settings.algorithm
    expires: int = settings.token_expiration

    # Token expiration times
    access_token_expires: int = 30 * 60  # 30 minutes
    refresh_token_expires: int = 30 * 24 * 60 * 60  # 30 days

    @classmethod
    def encode(cls, data: dict) -> str:
        return jwt.encode(data, cls.secret, algorithm=cls.algorithm)

    @classmethod
    def decode(cls, token: str) -> dict:
        try:
            return jwt.decode(token, cls.secret, algorithms=[cls.algorithm])
        except JWTError:
            raise UnauthorizedError("Invalid token")

    @classmethod
    def create(cls, user: UserInfo) -> str:
        """Create access token (legacy method for backward compatibility)"""
        return cls.create_access_token(user)

    @classmethod
    def create_access_token(cls, user: UserInfo) -> str:
        """Create a short-lived access token"""
        expire = datetime.utcnow() + timedelta(seconds=cls.access_token_expires)
        payload = {**user, "exp": expire, "type": "access"}
        return cls.encode(payload)

    @classmethod
    def create_refresh_token(cls, user: UserInfo) -> str:
        """Create a long-lived refresh token with minimal payload"""
        expire = datetime.utcnow() + timedelta(seconds=cls.refresh_token_expires)
        # Only include essential data for refresh tokens
        payload = {"identity": user.get("identity"), "username": user.get("username"), "exp": expire, "type": "refresh"}
        return cls.encode(payload)

    @classmethod
    def create_token_pair(cls, user: UserInfo) -> tuple[str, str]:
        """Create both access and refresh tokens"""
        access_token = cls.create_access_token(user)
        refresh_token = cls.create_refresh_token(user)
        return access_token, refresh_token

    @classmethod
    def validate_refresh_token(cls, token: str) -> dict:
        """Validate and decode a refresh token"""
        payload = cls.decode(token)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")
        return payload
