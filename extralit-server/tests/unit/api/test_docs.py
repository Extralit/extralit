from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_docs_redirect(async_client: "AsyncClient"):
    response = await async_client.get("/docs", follow_redirects=False)
    assert response.status_code == 307
    assert response.next_request.url.path == "/api/v1/docs"

    response = await async_client.get("/api", follow_redirects=False)
    assert response.status_code == 307
    assert response.next_request.url.path == "/api/v1/docs"
