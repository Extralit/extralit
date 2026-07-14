from __future__ import annotations

import os
from typing import Optional

from extralit.v2._api._transport import AsyncTransport
from extralit.v2.resources import Projections, Questions, Records, Responses, Schemas, Suggestions


def _credentials_fallback() -> tuple:
    # The single, documented v1 import: the credentials file outlives v1 retirement.
    from extralit.client.login import ExtralitCredentials

    if not ExtralitCredentials.exists():
        return None, None
    try:
        credentials = ExtralitCredentials.load()
        return credentials.api_url, credentials.api_key
    except (OSError, KeyError, ValueError):
        return None, None


class AsyncClient:
    """Async-native /api/v2 client. Resolution order for connection settings:
    explicit args > EXTRALIT_API_URL / EXTRALIT_API_KEY env > ~/.extralit/credentials.json."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 60.0,
        retries: int = 5,
    ):
        api_url = api_url or os.environ.get("EXTRALIT_API_URL")
        api_key = api_key or os.environ.get("EXTRALIT_API_KEY")
        if not api_url or (not api_key and not username):
            file_url, file_key = _credentials_fallback()
            api_url = api_url or file_url
            if not api_key and not username:
                api_key = file_key
        if not api_url:
            raise ValueError("api_url is required (argument, EXTRALIT_API_URL, or ~/.extralit/credentials.json)")
        if not api_key and not username:
            raise ValueError("credentials required: api_key or username/password")
        self._transport = AsyncTransport(
            api_url, api_key=api_key, username=username, password=password, timeout=timeout, retries=retries
        )
        self.schemas = Schemas(self._transport)
        self.questions = Questions(self._transport)
        self.records = Records(self._transport)
        self.suggestions = Suggestions(self._transport, self.questions)
        self.projections = Projections(self._transport)
        self.responses = Responses(self._transport)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()
