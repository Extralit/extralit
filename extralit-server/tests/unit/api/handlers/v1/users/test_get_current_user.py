import pytest
from httpx import AsyncClient

from extralit_server.models import User


@pytest.mark.asyncio
class TestGetCurrentUser:
    def url(self) -> str:
        return "/api/v1/me"

    async def test_get_current_user(self, async_client: AsyncClient, owner: User, owner_auth_header: dict):
        response = await async_client.get(self.url(), headers=owner_auth_header)

        assert response.status_code == 200
        assert response.json() == {
            "id": str(owner.id),
            "first_name": owner.first_name,
            "last_name": owner.last_name,
            "username": owner.username,
            "role": owner.role,
            "api_key": owner.api_key,
            "inserted_at": owner.inserted_at.isoformat(),
            "updated_at": owner.updated_at.isoformat(),
        }

    async def test_get_current_user_without_authentication(self, async_client: AsyncClient):
        response = await async_client.get(self.url())

        assert response.status_code == 401
