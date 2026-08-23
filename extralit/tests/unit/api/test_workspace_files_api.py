from unittest.mock import MagicMock

import pytest

from extralit._api._workspaces import WorkspacesAPI
from extralit._models._files import FileObjectResponse, ListObjectsResponse, ObjectMetadata


@pytest.fixture
def workspace_api():
    http_client = MagicMock()
    return WorkspacesAPI(http_client=http_client)


def test_list_files(workspace_api: WorkspacesAPI):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "objects": [
            {
                "workspace": "test-workspace",
                "object_name": "test-file.txt",
                "last_modified": "2023-01-01T00:00:00Z",
                "etag": "test-etag",
                "size": 100,
                "content_type": "text/plain",
                "metadata": {},
            }
        ]
    }
    workspace_api.http_client.get.return_value = mock_response  # type: ignore

    result = workspace_api.list_files("test-workspace", "test-path")

    assert isinstance(result, ListObjectsResponse)
    assert len(result.objects) == 1
    assert result.objects[0].workspace == "test-workspace"
    assert result.objects[0].object_name == "test-file.txt"

    workspace_api.http_client.get.assert_called_once_with(  # type: ignore
        url="/api/v1/files/test-workspace/test-path", params={"recursive": True}
    )


def test_get_file(workspace_api: WorkspacesAPI):
    """Test getting a file from a workspace."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"test content"
    mock_response.headers = {
        "Content-Type": "text/plain",
        "ETag": "test-etag",
    }
    workspace_api.http_client.get.return_value = mock_response

    result = workspace_api.get_file("test-workspace", "test-file.txt")

    assert isinstance(result, FileObjectResponse)
    assert result.content == b"test content"
    assert result.metadata.workspace == "test-workspace"
    assert result.metadata.object_name == "test-file.txt"
    assert result.metadata.content_type == "text/plain"
    assert result.metadata.etag == "test-etag"

    # Verify the API call
    workspace_api.http_client.get.assert_called_once_with(url="/api/v1/file/test-workspace/test-file.txt")


def test_put_file(workspace_api, tmp_path):
    """Test uploading a file to a workspace."""
    test_file = tmp_path / "test-file.txt"
    test_file.write_text("test content")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "workspace": "test-workspace",
        "object_name": "test-file.txt",
        "last_modified": "2023-01-01T00:00:00Z",
        "etag": "test-etag",
        "size": 100,
        "content_type": "text/plain",
        "metadata": {},
    }
    workspace_api.http_client.post.return_value = mock_response  # type: ignore

    result = workspace_api.put_file("test-workspace", "test-file.txt", test_file)

    assert isinstance(result, ObjectMetadata)
    assert result.workspace == "test-workspace"
    assert result.object_name == "test-file.txt"
    assert result.etag == "test-etag"

    workspace_api.http_client.post.assert_called_once()
    assert workspace_api.http_client.post.call_args.kwargs["url"] == "/api/v1/file/test-workspace/test-file.txt"


def test_delete_file(workspace_api: WorkspacesAPI):
    """Test deleting a file from a workspace."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    workspace_api.http_client.delete.return_value = mock_response  # type: ignore

    # Call the method
    workspace_api.delete_file("test-workspace", "test-file.txt")

    # Verify the API call
    workspace_api.http_client.delete.assert_called_once_with(url="/api/v1/file/test-workspace/test-file.txt")  # type: ignore
