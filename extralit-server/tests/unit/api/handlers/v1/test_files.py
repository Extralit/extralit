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

import io
import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

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
async def test_get_file(async_client: "AsyncClient"):
    # Use a simpler patching approach that works with the existing test setup
    with patch("extralit_server.contexts.files.get_s3_client") as mock_get_s3_client:
        # Create mock S3 client
        mock_s3_client = MagicMock()

        # Mock head_object as async
        async def mock_head_object(Bucket=None, Key=None, **kwargs):
            return {
                "ContentLength": 9,
                "ETag": '"test-etag"',
                "ContentType": "application/octet-stream",
            }

        mock_s3_client.head_object = mock_head_object

        # Mock get_object as async
        async def mock_get_object(Bucket=None, Key=None, **kwargs):
            # Create a simple async stream
            class MockBody:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if not hasattr(self, "_done"):
                        self._done = True
                        return b"test data"
                    raise StopAsyncIteration

            return {"Body": MockBody()}

        mock_s3_client.get_object = mock_get_object

        # Return the mock client from the patched function
        mock_get_s3_client.return_value = mock_s3_client

        file = MinioFileFactory.build()
        response = await async_client.get(f"/api/v1/file/{file.bucket_name}/{file.object_name}")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_put_file(async_client: "AsyncClient", owner_auth_header: dict):
    bucket_name = "workspace"
    object_name = "test_object"
    file_content = b"test file content"

    # Mock the Minio client and the response
    with patch("extralit_server.contexts.files.put_object") as mock_put_object:
        mock_response = ObjectMetadata(bucket_name=bucket_name, object_name=object_name, is_latest=True)
        mock_put_object.return_value = mock_response

        response = await async_client.post(
            f"/api/v1/file/{bucket_name}/{object_name}",
            files={"file": ("test.txt", io.BytesIO(file_content), "application/octet-stream")},
            headers=owner_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["object_name"] == mock_response.object_name
        assert response.json()["is_latest"] == mock_response.is_latest

        # Verify put_object was called correctly
        mock_put_object.assert_called_once()


@pytest.mark.asyncio
async def test_list_objects_non_workspace_user(async_client: "AsyncClient", annotator_auth_header: dict):
    bucket_name = "workspace"
    prefix = "test_prefix"

    response = await async_client.get(f"/api/v1/files/{bucket_name}/{prefix}", headers=annotator_auth_header)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_objects(async_client: "AsyncClient", owner_auth_header: dict):
    bucket_name = "workspace"
    prefix = "test_prefix"

    workspace_a = await WorkspaceFactory.create(name=bucket_name)
    user_a = await UserFactory.create(username="username-a")
    await WorkspaceUserFactory.create(workspace_id=workspace_a.id, user_id=user_a.id)

    # Mock the Minio client and the response
    with patch("extralit_server.contexts.files.list_objects") as mock_list_objects:
        mock_response = ListObjectsResponse(
            objects=[
                ObjectMetadata(bucket_name=bucket_name, object_name=f"{prefix}/test1"),
                ObjectMetadata(bucket_name=bucket_name, object_name=f"{prefix}/test2"),
            ]
        )
        mock_list_objects.return_value = mock_response

        response = await async_client.get(
            f"/api/v1/files/{bucket_name}/{prefix}", headers={API_KEY_HEADER_NAME: user_a.api_key}
        )

        assert response.status_code == 200
        assert response.json() == mock_response.dict()


@pytest.mark.asyncio
async def test_list_objects_with_versions(async_client: "AsyncClient", owner_auth_header: dict):
    bucket_name = "workspace-files"
    prefix = "schemas"
    object_name = os.path.join(prefix, "test")

    # Mock get_s3_client and bucket_exists
    with (
        patch("extralit_server.contexts.files.get_s3_client") as mock_get_s3_client,
        patch("extralit_server.contexts.files.delete_bucket"),
        patch("extralit_server.contexts.files.list_objects") as mock_list_objects,
    ):
        # Setup mocks
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_get_s3_client.return_value = mock_client

        # Create workspace and user
        workspace_a = await WorkspaceFactory.create(name=bucket_name)
        user_a = await UserFactory.create(username="username-a")
        await WorkspaceUserFactory.create(workspace_id=workspace_a.id, user_id=user_a.id)

        # Create mock objects for response
        file1 = MinioFileFactory.build(
            bucket_name=bucket_name, object_name=object_name, version_tag="v1", is_latest=False
        )
        file2 = MinioFileFactory.build(
            bucket_name=bucket_name, object_name=object_name, version_tag="v2", is_latest=True
        )

        # Set up list_objects mock
        mock_list_objects.return_value = ListObjectsResponse(
            objects=[
                ObjectMetadata(**file1.dict()),
                ObjectMetadata(**file2.dict()),
            ]
        )

        response = await async_client.get(
            f"/api/v1/files/{bucket_name}/{prefix}", headers={API_KEY_HEADER_NAME: user_a.api_key}
        )

        assert response.status_code == 200

        # Check versions
        response_objects = response.json()["objects"]
        assert len(response_objects) == 2

        # Check version tags
        response_version_tags = {item["version_tag"] for item in response_objects}
        assert response_version_tags == {"v1", "v2"}

        # Check latest flag
        for item in response_objects:
            if item["version_tag"] == "v2":
                assert item["is_latest"] is True
            else:
                assert item["is_latest"] is False


@pytest.mark.asyncio
async def test_delete_file(async_client: "AsyncClient", owner_auth_header: dict):
    bucket_name = "workspace"
    object_name = "test_object"

    # Create a test file
    file = MinioFileFactory.build(object_name=object_name, bucket_name=bucket_name)

    # Mock delete_object function
    with patch("extralit_server.contexts.files.delete_object") as mock_delete:
        mock_delete.return_value = None

        response = await async_client.delete(
            f"/api/v1/file/{file.bucket_name}/{file.object_name}", headers=owner_auth_header
        )

        assert response.status_code == 200
        assert response.json() == {"message": "File deleted"}

        # Verify delete was called - use any_call instead of specific argument checking
        assert mock_delete.called
