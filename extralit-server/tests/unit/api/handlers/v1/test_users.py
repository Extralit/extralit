from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.models import UserRole
from tests.factories import UserFactory, WorkspaceFactory

if TYPE_CHECKING:
    pass


@pytest.mark.asyncio
class TestsUsersV1Endpoints:
    async def test_list_user_workspaces(self, async_client: "AsyncClient", owner_auth_header: dict):
        workspaces = await WorkspaceFactory.create_batch(3)
        user = await UserFactory.create(workspaces=workspaces)

        response = await async_client.get(f"/api/v1/users/{user.id}/workspaces", headers=owner_auth_header)

        assert response.status_code == 200
        assert response.json() == {
            "items": [
                {
                    "id": str(workspace.id),
                    "name": workspace.name,
                    "inserted_at": workspace.inserted_at.isoformat(),
                    "updated_at": workspace.updated_at.isoformat(),
                }
                for workspace in workspaces
            ]
        }

    async def test_list_user_workspaces_for_owner(self, async_client: "AsyncClient"):
        workspaces = await WorkspaceFactory.create_batch(5)
        owner = await UserFactory.create(role=UserRole.owner)

        response = await async_client.get(
            f"/api/v1/users/{owner.id}/workspaces", headers={API_KEY_HEADER_NAME: owner.api_key}
        )
        assert response.status_code == 200
        assert response.json() == {
            "items": [
                {
                    "id": str(workspace.id),
                    "name": workspace.name,
                    "inserted_at": workspace.inserted_at.isoformat(),
                    "updated_at": workspace.updated_at.isoformat(),
                }
                for workspace in workspaces
            ]
        }

    @pytest.mark.parametrize("role", [UserRole.annotator, UserRole.admin])
    async def test_list_user_workspaces_as_restricted_user(self, async_client: "AsyncClient", role: UserRole):
        workspaces = await WorkspaceFactory.create_batch(3)
        user = await UserFactory.create(workspaces=workspaces)
        requesting_user = await UserFactory.create(role=role)

        response = await async_client.get(
            f"/api/v1/users/{user.id}/workspaces", headers={API_KEY_HEADER_NAME: requesting_user.api_key}
        )

        assert response.status_code == 403

    async def test_list_user_workspaces_for_non_existing_user(
        self, async_client: "AsyncClient", owner_auth_header: dict
    ):
        user_id = uuid4()

        response = await async_client.get(
            f"/api/v1/users/{user_id}/workspaces",
            headers=owner_auth_header,
        )

        assert response.status_code == 404
        assert response.json() == {"detail": f"User with id `{user_id}` not found"}
