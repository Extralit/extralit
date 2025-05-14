import io
from typing import TYPE_CHECKING
from uuid import uuid4
from unittest.mock import patch, MagicMock

import pytest
from argilla_server.contexts.files import delete_bucket, get_minio_client
from argilla_server.schemas.v1.files import ListObjectsResponse, ObjectMetadata
from argilla_server.constants import API_KEY_HEADER_NAME
from argilla_server.schemas.v1.questions import QUESTION_CREATE_DESCRIPTION_MAX_LENGTH, QUESTION_CREATE_TITLE_MAX_LENGTH

from tests.factories import (
    MinioFileFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceUserFactory,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_file(async_client: "AsyncClient"):
    # Mock the Minio client andthe response
    file = MinioFileFactory.create()

    response = await async_client.get(f"/api/v1/file/{file.bucket_name}/{file.object_name}")

    assert response.status_code == 200
    assert response.content == b"test data"


@pytest.mark.asyncio
async def test_put_file(async_client: "AsyncClient", owner_auth_header: dict):
    bucket_name = "workspace"
    object_name = "test_object"
    file_content = b"test file content"
    
    # Mock the Minio client and the response
    with patch("argilla_server.contexts.files.get_minio_client") as mock_get_minio_client:
        mock_client = MagicMock()
        mock_get_minio_client.return_value = mock_client
        
        mock_response = ObjectMetadata(
            bucket_name=bucket_name,
            object_name=object_name,
            is_latest=True
        )
        mock_client.put_object.return_value = mock_response
        
        response = await async_client.post(
            f"/api/v1/file/{bucket_name}/{object_name}", 
            files={"file": ("test.txt", io.BytesIO(file_content), "application/octet-stream")},
            headers=owner_auth_header
        )
        
        assert response.status_code == 200
        assert response.json()['object_name'] == mock_response.object_name
        assert response.json()['is_latest'] == mock_response.is_latest


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
    with patch("argilla_server.contexts.files.list_objects") as mock_list_objects:
        mock_response = ListObjectsResponse(objects=[
            ObjectMetadata(bucket_name=bucket_name, object_name=f"{prefix}/test1"),
            ObjectMetadata(bucket_name=bucket_name, object_name=f"{prefix}/test2"),
        ])
        mock_list_objects.return_value = mock_response
        
        response = await async_client.get(
            f"/api/v1/files/{bucket_name}/{prefix}", 
            headers={API_KEY_HEADER_NAME: user_a.api_key}
        )
        
        assert response.status_code == 200
        assert response.json() == mock_response.dict()


@pytest.mark.asyncio
async def test_list_objects_with_versions(async_client: "AsyncClient", owner_auth_header: dict):
    bucket_name = "workspace-files"
    prefix = "schemas"
    object_name = f"{prefix}/test"
    client = get_minio_client()

    if client.bucket_exists(bucket_name):
        delete_bucket(client=client, workspace_name=bucket_name)

    workspace_a = await WorkspaceFactory.create(name=bucket_name)
    user_a = await UserFactory.create(username="username-a")
    await WorkspaceUserFactory.create(workspace_id=workspace_a.id, user_id=user_a.id)
    
    # Create two files with the same object_name
    file1 = MinioFileFactory.create(bucket_name=bucket_name, object_name=object_name)
    file2 = MinioFileFactory.create(bucket_name=bucket_name, object_name=object_name)
    
    expected_response = ListObjectsResponse(objects=[
        ObjectMetadata(**file1.dict(exclude={"version_tag", "is_latest"}), version_tag="v1", is_latest=False),
        ObjectMetadata(**file2.dict(exclude={"version_tag", "is_latest"}), version_tag="v2", is_latest=True),
    ])
    
    response = await async_client.get(
        f"/api/v1/files/{bucket_name}/{prefix}", 
        headers={API_KEY_HEADER_NAME: user_a.api_key}
    )
    
    assert response.status_code == 200

    # Assert that the sets of version_tag values are the same
    response_version_tags = {item['version_tag'] for item in response.json()['objects']}
    expected_version_tags = {item.version_tag for item in expected_response.objects}
    assert response_version_tags == expected_version_tags

    # Assert that file2 is the latest version
    for item in response.json()['objects']:
        if item['version_tag'] == 'v2':
            assert item['is_latest'] is True
        else:
            assert item['is_latest'] is False


@pytest.mark.asyncio
async def test_delete_file(async_client: "AsyncClient", owner_auth_header: dict):
    bucket_name = "workspace"
    object_name = "test_object"
    
    file = MinioFileFactory.create(object_name=object_name, bucket_name=bucket_name)

    response = await async_client.delete(
        f"/api/v1/file/{file.bucket_name}/{file.object_name}", 
        headers=owner_auth_header
    )
    
    assert response.status_code == 200
    assert response.json() == {"message": "File deleted"}

    response = await async_client.get(f"/api/v1/file/{file.bucket_name}/{file.object_name}")
    assert response.status_code == 404