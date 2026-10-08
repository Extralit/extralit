from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.enums import UserRole
from tests.factories import UserFactory


@pytest.mark.asyncio
class TestGetUser:
    def url(self, user_id: UUID) -> str:
        return f"/api/v1/users/{user_id}"

    async def test_get_user(self, async_client: AsyncClient, owner_auth_header: dict):
        user = await UserFactory.create()

        response = await async_client.get(self.url(user.id), headers=owner_auth_header)

        assert response.status_code == 200
        assert response.json() == {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "role": UserRole.annotator,
            "api_key": user.api_key,
            "inserted_at": user.inserted_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

    async def test_get_user_without_authentication(self, async_client: AsyncClient):
        user = await UserFactory.create()

        response = await async_client.get(self.url(user.id))

        assert response.status_code == 401

    @pytest.mark.parametrize("user_role", [UserRole.admin, UserRole.annotator])
    async def test_get_user_with_unauthorized_role(self, async_client: AsyncClient, user_role: UserRole):
        user = await UserFactory.create(role=user_role)

        response = await async_client.get(
            self.url(user.id),
            headers={API_KEY_HEADER_NAME: user.api_key},
        )

        assert response.status_code == 403

    async def test_get_user_with_nonexistent_user_id(self, async_client: AsyncClient, owner_auth_header: dict):
        user_id = uuid4()

        response = await async_client.get(self.url(user_id), headers=owner_auth_header)

        assert response.status_code == 404
        assert response.json() == {"detail": f"User with id `{user_id}` not found"}
