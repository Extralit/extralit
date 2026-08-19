from unittest.mock import patch

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

        # Mock S3 client and Redis connection
        with (
            patch("extralit_server.contexts.files.bucket_exists") as mock_bucket_exists,
            patch("extralit_server.jobs.queues.DEFAULT_QUEUE") as mock_queue,
        ):
            mock_bucket_exists.return_value = True
            mock_queue.connection.ping.return_value = True

            response = await async_client.post(
                self.url(str(workspace.id)),
                headers=owner_auth_header,
                params={"autofix": True},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["workspace_id"] == str(workspace.id)
            assert data["workspace_name"] == workspace.name
            assert data["overall_status"] == "healthy"
            assert len(data["checks"]) >= 2  # At least the bucket and RQ checks

            # Check that bucket check passed
            bucket_check = next((c for c in data["checks"] if c["check_name"] == "s3_bucket"), None)
            assert bucket_check is not None
            assert bucket_check["status"] == "ok"
            assert bucket_check["fixed"] is False

    async def test_workspace_doctor_missing_bucket_with_autofix(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        workspace = await WorkspaceFactory.create()

        with (
            patch("extralit_server.contexts.files.bucket_exists") as mock_bucket_exists,
            patch("extralit_server.contexts.files.create_bucket") as mock_create_bucket,
            patch("extralit_server.jobs.queues.DEFAULT_QUEUE") as mock_queue,
        ):
            mock_bucket_exists.return_value = False
            mock_create_bucket.return_value = None
            mock_queue.connection.ping.return_value = True

            response = await async_client.post(
                self.url(str(workspace.id)),
                headers=owner_auth_header,
                params={"autofix": True},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["overall_status"] == "issues_fixed"

            # Check that bucket was created
            bucket_check = next((c for c in data["checks"] if c["check_name"] == "s3_bucket"), None)
            assert bucket_check is not None
            assert bucket_check["status"] == "ok"
            assert bucket_check["fixed"] is True
            assert "created" in bucket_check["message"].lower()

            # Verify create_bucket was called
            mock_create_bucket.assert_called_once()

    async def test_workspace_doctor_missing_bucket_without_autofix(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        workspace = await WorkspaceFactory.create()

        with (
            patch("extralit_server.contexts.files.bucket_exists") as mock_bucket_exists,
            patch("extralit_server.contexts.files.create_bucket") as mock_create_bucket,
            patch("extralit_server.jobs.queues.DEFAULT_QUEUE") as mock_queue,
        ):
            mock_bucket_exists.return_value = False
            mock_queue.connection.ping.return_value = True

            response = await async_client.post(
                self.url(str(workspace.id)),
                headers=owner_auth_header,
                params={"autofix": False},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["overall_status"] == "issues_found"

            # Check that bucket error is reported
            bucket_check = next((c for c in data["checks"] if c["check_name"] == "s3_bucket"), None)
            assert bucket_check is not None
            assert bucket_check["status"] == "error"
            assert bucket_check["fixed"] is False

            # Verify create_bucket was NOT called
            mock_create_bucket.assert_not_called()

    async def test_workspace_doctor_without_authentication(self, db: AsyncSession, async_client: AsyncClient):
        workspace = await WorkspaceFactory.create()

        response = await async_client.post(
            self.url(str(workspace.id)),
            params={"autofix": True},
        )

        assert response.status_code == 401

    async def test_workspace_doctor_nonexistent_workspace(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        from uuid import uuid4

        fake_id = uuid4()
        response = await async_client.post(
            self.url(str(fake_id)),
            headers=owner_auth_header,
            params={"autofix": True},
        )

        assert response.status_code == 404
