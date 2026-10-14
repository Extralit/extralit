import pytest
from httpx import AsyncClient

from extralit_server._version import __version__


@pytest.mark.asyncio
class TestGetVersion:
    def url(self) -> str:
        return "/api/v1/version"

    async def test_get_version(self, async_client: AsyncClient):
        response = await async_client.get(self.url())

        assert response.status_code == 200
        assert response.json() == {"version": __version__}
