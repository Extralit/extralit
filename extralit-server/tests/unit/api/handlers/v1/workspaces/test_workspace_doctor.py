from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import WorkspaceFactory


@pytest.mark.asyncio
class TestWorkspaceDoctor:
    def url(self, workspace_id: str) -> str:
        return f"/api/v1/workspaces/{workspace_id}/doctor"

    async def test_workspace_doctor_healthy(self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict):
        workspace = await WorkspaceFactory.create()

        with (
            patch("extralit_server.contexts.files.ObjectStorage.healthy", AsyncMock(return_value=True)),
            patch("extralit_server.jobs.queues.DEFAULT_QUEUE") as mock_queue,
        ):
            mock_queue.connection.ping.return_value = True

            response = await async_client.post(self.url(str(workspace.id)), headers=owner_auth_header)

            assert response.status_code == 200
            data = response.json()

            assert data["workspace_id"] == str(workspace.id)
            assert data["workspace_name"] == workspace.name
            assert data["overall_status"] == "healthy"

            storage_check = next(c for c in data["checks"] if c["check_name"] == "storage")
            assert storage_check["status"] == "ok"
            assert storage_check["fixed"] is False

    async def test_workspace_doctor_unreachable_storage(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        workspace = await WorkspaceFactory.create()

        with (
            patch("extralit_server.contexts.files.ObjectStorage.healthy", AsyncMock(return_value=False)),
            patch("extralit_server.jobs.queues.DEFAULT_QUEUE") as mock_queue,
        ):
            mock_queue.connection.ping.return_value = True

            response = await async_client.post(self.url(str(workspace.id)), headers=owner_auth_header)

            assert response.status_code == 200
            data = response.json()

            assert data["overall_status"] == "issues_found"
            storage_check = next(c for c in data["checks"] if c["check_name"] == "storage")
            assert storage_check["status"] == "error"
            assert storage_check["fixed"] is False

    async def test_workspace_doctor_without_authentication(self, db: AsyncSession, async_client: AsyncClient):
        workspace = await WorkspaceFactory.create()

        response = await async_client.post(self.url(str(workspace.id)), params={"autofix": True})

        assert response.status_code == 401

    async def test_workspace_doctor_nonexistent_workspace(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        from uuid import uuid4

        response = await async_client.post(self.url(str(uuid4())), headers=owner_auth_header, params={"autofix": True})

        assert response.status_code == 404
