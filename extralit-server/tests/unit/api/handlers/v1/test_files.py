import io
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.contexts.files import ListObjectsResponse, ObjectMetadata
from tests.factories import (
    MinioFileFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceUserFactory,
)

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_put_file(async_client: "AsyncClient", owner_auth_header: dict):
    workspace = "workspace"
    object_name = "test_object"
    file_content = b"test file content"

    # Mock the Minio client and the response
    with patch("extralit_server.contexts.files.put_object") as mock_put_object:
        mock_response = ObjectMetadata(workspace=workspace, object_name=object_name)
        mock_put_object.return_value = mock_response

        response = await async_client.post(
            f"/api/v1/file/{workspace}/{object_name}",
            files={"file": ("test.txt", io.BytesIO(file_content), "application/octet-stream")},
            headers=owner_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["object_name"] == mock_response.object_name

        # Verify put_object was called correctly
        mock_put_object.assert_called_once()


@pytest.mark.asyncio
async def test_get_file_without_auth(async_client: "AsyncClient"):
    response = await async_client.get("/api/v1/file/workspace/test_object")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_objects_without_auth(async_client: "AsyncClient"):
    response = await async_client.get("/api/v1/files/workspace/test_prefix")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_objects_non_workspace_user(async_client: "AsyncClient", annotator_auth_header: dict):
    workspace = "workspace"
    prefix = "test_prefix"

    response = await async_client.get(f"/api/v1/files/{workspace}/{prefix}", headers=annotator_auth_header)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_objects(async_client: "AsyncClient", owner_auth_header: dict):
    workspace = "workspace"
    prefix = "test_prefix"

    workspace_a = await WorkspaceFactory.create(name=workspace)
    user_a = await UserFactory.create(username="username-a")
    await WorkspaceUserFactory.create(workspace_id=workspace_a.id, user_id=user_a.id)

    # Mock the Minio client and the response
    with patch("extralit_server.contexts.files.list_objects") as mock_list_objects:
        mock_response = ListObjectsResponse(
            objects=[
                ObjectMetadata(workspace=workspace, object_name=f"{prefix}/test1"),
                ObjectMetadata(workspace=workspace, object_name=f"{prefix}/test2"),
            ]
        )
        mock_list_objects.return_value = mock_response

        response = await async_client.get(
            f"/api/v1/files/{workspace}/{prefix}", headers={API_KEY_HEADER_NAME: user_a.api_key}
        )

        assert response.status_code == 200
        assert response.json() == mock_response.dict()


@pytest.mark.asyncio
async def test_delete_file(async_client: "AsyncClient", owner_auth_header: dict):
    workspace = "workspace"
    object_name = "test_object"

    # Create a test file
    file = MinioFileFactory.build(object_name=object_name, workspace=workspace)

    # Mock delete_object function
    with patch("extralit_server.contexts.files.delete_object") as mock_delete:
        mock_delete.return_value = None

        response = await async_client.delete(
            f"/api/v1/file/{file.workspace}/{file.object_name}", headers=owner_auth_header
        )

        assert response.status_code == 200
        assert response.json() == {"message": "File deleted"}

        # Verify delete was called - use any_call instead of specific argument checking
        assert mock_delete.called
