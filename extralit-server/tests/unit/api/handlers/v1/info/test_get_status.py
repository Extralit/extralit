import pytest
from httpx import AsyncClient

from extralit_server._version import __version__
from extralit_server.search_engine import SearchEngine


@pytest.mark.asyncio
class TestGetStatus:
    def url(self) -> str:
        return "/api/v1/status"

    async def test_get_status(self, async_client: AsyncClient, mock_search_engine: SearchEngine):
        mock_search_engine.info.return_value = {}

        response = await async_client.get(self.url())

        assert response.status_code == 200

        response_json = response.json()
        assert response_json["version"] == __version__
        assert "search_engine" in response_json
        assert "memory" in response_json
