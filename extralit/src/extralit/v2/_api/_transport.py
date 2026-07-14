from __future__ import annotations

from typing import Any, Optional

import httpx

from extralit.v2._api._errors import AuthError, error_from_response

_API_PREFIX = "/api/v2"


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


class AsyncTransport:
    """One httpx.AsyncClient per client instance. Auth modes: api_key header (default,
    no token lifecycle) or username/password -> bearer JWT with a single transparent
    refresh on 401 (then AuthError)."""

    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 60.0,
        retries: int = 5,
        extra_headers: Optional[dict] = None,
    ):
        self.api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._username = username
        self._password = password
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._http = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=timeout,
            transport=httpx.AsyncHTTPTransport(retries=retries),
            headers=extra_headers or {},
        )

    def _auth_headers(self) -> dict:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        if self._api_key:
            return {"X-Extralit-Api-Key": self._api_key}
        return {}

    async def _login(self) -> None:
        response = await self._http.post(
            f"{_API_PREFIX}/token", data={"username": self._username, "password": self._password}
        )
        if response.status_code >= 400:
            raise AuthError(response.status_code, _safe_json(response))
        payload = response.json()
        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token")

    async def _refresh(self) -> bool:
        if not self._refresh_token:
            return False
        response = await self._http.post(f"{_API_PREFIX}/token/refresh", json={"refresh_token": self._refresh_token})
        if response.status_code >= 400:
            return False
        payload = response.json()
        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token", self._refresh_token)
        return True

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
    ) -> Any:
        if self._username and not self._access_token and not self._api_key:
            await self._login()
        response = await self._http.request(
            method, f"{_API_PREFIX}{path}", params=params, json=json, headers=self._auth_headers()
        )
        if response.status_code == 401 and self._access_token and await self._refresh():
            response = await self._http.request(
                method, f"{_API_PREFIX}{path}", params=params, json=json, headers=self._auth_headers()
            )
        if response.status_code >= 400:
            raise error_from_response(response.status_code, _safe_json(response))
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def aclose(self) -> None:
        await self._http.aclose()
