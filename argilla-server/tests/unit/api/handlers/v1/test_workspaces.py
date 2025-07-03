# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from uuid import uuid4

import pytest
from argilla_server.constants import API_KEY_HEADER_NAME
from argilla_server.models import UserRole
from httpx import AsyncClient

from tests.factories import AnnotatorFactory, DatasetFactory, UserFactory, WorkspaceFactory


@pytest.mark.asyncio
class TestSuiteWorkspaces:
    async def test_get_workspace(self, async_client: AsyncClient, owner_auth_header: dict):
        workspace = await WorkspaceFactory.create(name="workspace")

        response = await async_client.get(f"/api/v1/workspaces/{workspace.id}", headers=owner_auth_header)

        assert response.status_code == 200
        assert response.json() == {
            "id": str(workspace.id),
            "name": "workspace",
            "inserted_at": workspace.inserted_at.isoformat(),
            "updated_at": workspace.updated_at.isoformat(),
        }

    async def test_get_workspace_without_authentication(self, async_client: AsyncClient):
        workspace = await WorkspaceFactory.create()

        response = await async_client.get(f"/api/v1/workspaces/{workspace.id}")

        assert response.status_code == 401

    async def test_get_workspace_as_annotator(self, async_client: AsyncClient):
        workspace = await WorkspaceFactory.create(name="workspace")
        annotator = await AnnotatorFactory.create(workspaces=[workspace])

        response = await async_client.get(
            f"/api/v1/workspaces/{workspace.id}", headers={API_KEY_HEADER_NAME: annotator.api_key}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "workspace"

    async def test_get_workspace_as_annotator_from_different_workspace(self, async_client: AsyncClient):
        workspace = await WorkspaceFactory.create()
        another_workspace = await WorkspaceFactory.create()
        annotator = await AnnotatorFactory.create(workspaces=[another_workspace])

        response = await async_client.get(
            f"/api/v1/workspaces/{workspace.id}", headers={API_KEY_HEADER_NAME: annotator.api_key}
        )

        assert response.status_code == 403

    async def test_get_workspace_with_nonexistent_workspace_id(
        self, async_client: AsyncClient, owner_auth_header: dict
    ):
        workspace_id = uuid4()

        await WorkspaceFactory.create()

        response = await async_client.get(
            f"/api/v1/workspaces/{workspace_id}",
            headers=owner_auth_header,
        )

        assert response.status_code == 404
        assert response.json() == {"detail": f"Workspace with id `{workspace_id}` not found"}

    @pytest.mark.skip(reason="Failing with 500 instead of 200 status code")
    async def test_delete_workspace(self, async_client: AsyncClient, owner_auth_header: dict):
        workspace = await WorkspaceFactory.create(name="workspace_delete")
        other_workspace = await WorkspaceFactory.create()

        await DatasetFactory.create_batch(3, workspace=other_workspace)

        response = await async_client.delete(f"/api/v1/workspaces/{workspace.id}", headers=owner_auth_header)

        assert response.status_code == 200

    @pytest.mark.skip(reason="Failing with 500 instead of 409 status code")
    async def test_delete_workspace_with_feedback_datasets(self, async_client: AsyncClient, owner_auth_header: dict):
        workspace = await WorkspaceFactory.create(name="workspace_delete")

        await DatasetFactory.create_batch(3, workspace=workspace)

        response = await async_client.delete(f"/api/v1/workspaces/{workspace.id}", headers=owner_auth_header)

        assert response.status_code == 409
        assert response.json() == {
            "detail": f"Cannot delete the workspace {workspace.id}. This workspace has some datasets linked"
        }

    @pytest.mark.skip(reason="Failing with 500 instead of 404 status code")
    async def test_delete_missing_workspace(self, async_client: "AsyncClient", owner_auth_header: dict):
        workspace_id = uuid4()

        response = await async_client.delete(
            f"/api/v1/workspaces/{workspace_id}",
            headers=owner_auth_header,
        )

        assert response.status_code == 404
        assert response.json() == {"detail": f"Workspace with id `{workspace_id}` not found"}

    @pytest.mark.skip(reason="Failing with 500 instead of 403 status code")
    @pytest.mark.parametrize("role", [UserRole.annotator, UserRole.admin])
    async def test_delete_workspace_without_permissions(self, async_client: AsyncClient, role: UserRole):
        workspace = await WorkspaceFactory.create(name="workspace_delete")

        user = await UserFactory.create(role=role, workspaces=[workspace])
        async_client.headers.update({API_KEY_HEADER_NAME: user.api_key})
        response = await async_client.delete(f"/api/v1/workspaces/{workspace.id}")

        assert response.status_code == 403

    @pytest.mark.parametrize("role", [UserRole.owner, UserRole.admin, UserRole.annotator])
    async def test_list_workspaces_me(self, async_client: AsyncClient, role: UserRole) -> None:
        workspaces = await WorkspaceFactory.create_batch(size=5)
        user = await UserFactory.create(role=role, workspaces=workspaces if role != UserRole.owner else [])

        response = await async_client.get("/api/v1/me/workspaces", headers={API_KEY_HEADER_NAME: user.api_key})

        assert response.status_code == 200
        assert len(response.json()["items"]) == len(workspaces)
        for workspace in workspaces:
            assert {
                "id": str(workspace.id),
                "name": workspace.name,
                "inserted_at": workspace.inserted_at.isoformat(),
                "updated_at": workspace.updated_at.isoformat(),
            } in response.json()["items"]

    async def test_list_workspaces_me_without_authentication(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/v1/me/workspaces")

        assert response.status_code == 401

    @pytest.mark.parametrize("role", [UserRole.owner, UserRole.admin, UserRole.annotator])
    async def test_list_workspaces_me_no_workspaces(self, async_client: AsyncClient, role: UserRole) -> None:
        user = await UserFactory.create(role=role)

        response = await async_client.get("/api/v1/me/workspaces", headers={API_KEY_HEADER_NAME: user.api_key})

        assert response.status_code == 200
        assert len(response.json()["items"]) == 0

    # Schema Configuration Tests
    async def test_get_workspace_schema_configuration_empty(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test getting schema configuration from workspace with no metadata."""
        workspace = await WorkspaceFactory.create(name="test-workspace")

        response = await async_client.get(
            f"/api/v1/workspaces/{workspace.id}/schema-configuration", 
            headers=owner_auth_header
        )

        assert response.status_code == 200
        assert response.json() == {
            "schemas": [],
            "last_sync": None
        }

    async def test_get_workspace_schema_configuration_with_metadata(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test getting schema configuration from workspace with metadata."""
        workspace = await WorkspaceFactory.create(
            name="test-workspace",
            metadata_={
                "schema_configuration": {
                    "schemas": [
                        {
                            "name": "test_schema",
                            "is_singleton": True,
                            "s3_path": "schemas/test_schema.json",
                            "version_id": "abc123",
                            "dependencies": []
                        }
                    ],
                    "last_sync": "2024-01-01T00:00:00Z"
                }
            }
        )

        response = await async_client.get(
            f"/api/v1/workspaces/{workspace.id}/schema-configuration", 
            headers=owner_auth_header
        )

        assert response.status_code == 200
        assert response.json()["schemas"][0]["name"] == "test_schema"
        assert response.json()["schemas"][0]["is_singleton"] is True
        assert response.json()["last_sync"] == "2024-01-01T00:00:00Z"

    async def test_update_workspace_schema_configuration(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test updating workspace schema configuration."""
        workspace = await WorkspaceFactory.create(name="test-workspace")

        update_data = {
            "schema_configuration": {
                "schemas": [
                    {
                        "name": "new_schema",
                        "is_singleton": False,
                        "s3_path": "schemas/new_schema.json", 
                        "version_id": "def456",
                        "dependencies": []
                    }
                ]
            }
        }

        response = await async_client.put(
            f"/api/v1/workspaces/{workspace.id}/schema-configuration",
            headers=owner_auth_header,
            json=update_data
        )

        assert response.status_code == 200
        assert response.json()["schemas"][0]["name"] == "new_schema"
        assert response.json()["schemas"][0]["is_singleton"] is False

    async def test_get_workspace_schema_configuration_without_auth(self, async_client: AsyncClient):
        """Test getting schema configuration without authentication."""
        workspace = await WorkspaceFactory.create()

        response = await async_client.get(f"/api/v1/workspaces/{workspace.id}/schema-configuration")

        assert response.status_code == 401

    async def test_validate_workspace_schemas_empty(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test validating schemas in workspace with no schemas."""
        workspace = await WorkspaceFactory.create(name="test-workspace")

        response = await async_client.get(
            f"/api/v1/workspaces/{workspace.id}/schemas/validate",
            headers=owner_auth_header
        )

        assert response.status_code == 200
        assert response.json()["validation_results"] == []
        assert response.json()["all_valid"] is True
