import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.parametrize("http_method", ["GET", "POST", "PUT", "DELETE", "PATCH"])
@pytest.mark.parametrize("not_found_endpoint", ["/api/not/found/route", "/api/v1/not-found"])
async def test_route_not_found_response(async_client: AsyncClient, http_method: str, not_found_endpoint: str):
    response = await async_client.request(method=http_method, url=not_found_endpoint)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
