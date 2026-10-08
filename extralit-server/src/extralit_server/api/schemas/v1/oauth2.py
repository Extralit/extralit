from pydantic import BaseModel


class Provider(BaseModel):
    name: str


class Providers(BaseModel):
    items: list[Provider]


class Token(BaseModel):
    """Token response model"""

    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""

    refresh_token: str
