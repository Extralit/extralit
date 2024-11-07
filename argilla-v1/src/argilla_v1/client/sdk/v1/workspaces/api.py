#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os, hashlib
from pathlib import Path
from typing import Dict, List, Union, Optional
from uuid import UUID

import httpx

from argilla.client.sdk.commons.errors_handler import handle_response_error
from argilla.client.sdk.commons.models import ErrorMessage, HTTPValidationError, Response
from argilla.client.sdk.v1.workspaces.models import WorkspaceModel
from argilla.client.sdk.v1.files.models import ObjectMetadata, ListObjectsResponse, FileObjectResponse


def compute_file_hash(file_path: Path) -> str:
    """Calculate the MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_workspace(client: httpx.Client, id: UUID) -> Response[Union[WorkspaceModel, ErrorMessage, HTTPValidationError]]:
    """Sends a GET request to `/api/v1/workspaces/{id}` endpoint to retrieve a workspace.

    Args:
        client: the authenticated Argilla client to be used to send the request to the API.
        id: the id of the workspace to be retrieved.

    Returns:
        A `Response` object with the parsed response, containing a `parsed` attribute with the
        parsed response if the request was successful, which is an instance of `WorkspaceModel`.
    """
    url = f"/api/v1/workspaces/{id}"

    response = client.get(url=url)

    if response.status_code == 200:
        response_obj = Response.from_httpx_response(response)
        response_obj.parsed = WorkspaceModel(**response.json())
        return response_obj
    return handle_response_error(response)


def delete_workspace(
    client: httpx.Client, id: UUID
) -> Response[Union[WorkspaceModel, ErrorMessage, HTTPValidationError]]:
    url = f"/api/v1/workspaces/{id}"

    response = client.delete(url=url)

    if response.status_code == 200:
        response_obj = Response.from_httpx_response(response)
        response_obj.parsed = WorkspaceModel(**response.json())
        return response_obj
    return handle_response_error(response)


def delete_workspace_documents(
    client: httpx.Client, id: UUID
) -> Response[Union[WorkspaceModel, ErrorMessage, HTTPValidationError]]:
    url = f"/api/v1/documents/workspace/{id}"

    response = client.delete(url=url)

    if response.status_code == 200:
        response_obj = Response.from_httpx_response(response)
        return response_obj
    return handle_response_error(response)


def get_workspace_file(
    client: httpx.Client, workspace_name: str, path: str, version_id: Optional[str] = None
) -> Response[Union[str, ErrorMessage, HTTPValidationError]]:
    """Sends a GET request to `/file/{bucket}/{object}` endpoint to get a file.

    Args:
        client: the authenticated client to be used to send the request to the API.
        workspace_name: the name of the bucket.
        path: the name of the object.
        version_id: the version id of the object. Optional.

    Returns:
        A `Response` object containing the response from the server.
    """
    endpoint = f"/api/v1/file/{workspace_name}/{path}"
    params = {"version_id": version_id} if version_id else {}
    response = client.get(url=endpoint, params=params)

    if response.status_code == 200:
        response_obj = Response.from_httpx_response(response)
        response_obj.parsed = response.text
        return response_obj
    return handle_response_error(response)


def list_workspace_files(
    client: httpx.Client, workspace_name: str, path: str, recursive=True, include_version=True
) -> Response[Union[ListObjectsResponse, ErrorMessage, HTTPValidationError]]:
    """Sends a GET request to `/files/{bucket}/{prefix}` endpoint to list objects.

    Args:
        client: the authenticated client to be used to send the request to the API.
        workspace_name: the name of the bucket.
        prefix: the prefix of the objects. Optional.
        include_version: whether to include version information. Optional.

    Returns:
        A `Response` object containing the response from the server.
    """
    endpoint = f"/api/v1/files/{workspace_name}/{path}"
    params = {"include_version": include_version, "recursive": recursive}
    response = client.get(url=endpoint, params=params)

    if response.status_code == 200:
        response_obj = Response.from_httpx_response(response)
        response_obj.parsed = ListObjectsResponse(**response.json())
        return response_obj
    return handle_response_error(response)


def exist_workspace_file(client: httpx.Client, workspace_name: str, path: str, file_path: Path) -> Optional[ObjectMetadata]:
    """Check if the given `file_path` with the same hash already exists in the workspace.

    Args:
        client: The HTTP client used for making requests.
        workspace_name: The name of the workspace.
        path: The path in the workspace where the file would be located.
        file_path: The local path of the file to check.

    Returns:
        True if a matching file exists, False otherwise.
    """
    try:
        existing_files_response = list_workspace_files(client, workspace_name, path)
        if existing_files_response.status_code == 200:
            existing_files: ListObjectsResponse = existing_files_response.parsed
            file_hash = compute_file_hash(file_path)
            for file in existing_files.objects:
                if file.etag and file.object_name.endswith(file_path.name) and file.etag.strip('"') == file_hash:
                    return file
                
    except Exception as e:
        print(f"Error while checking if file exists: {e}")
        return None
            
    return None


def put_workspace_file(
    client: httpx.Client, workspace_name: str, path: str, file_path: Path
) -> Response[Union[ObjectMetadata, ErrorMessage, HTTPValidationError]]:
    """Sends a POST request to `/file/{bucket}/{object}` endpoint to upload a file.

    Args:
        client: the authenticated client to be used to send the request to the API.
        workspace_name: the name of the bucket.
        path: the name of the object.
        file_path: the file to be uploaded.

    Returns:
        A `Response` object containing the response from the server.
    """
    endpoint = f"/api/v1/file/{workspace_name}/{path}"
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as file_data:
        files = {"file": (file_name, file_data, "application/octet-stream")}
        response = client.post(url=endpoint, files=files)

    if response.status_code == 200:
        response_obj = Response.from_httpx_response(response)
        response_obj.parsed = ObjectMetadata(**response.json())
        return response_obj
    return handle_response_error(response)


def delete_workspace_file(client: httpx.Client, workspace_name: str, path: str, version_id: Optional[str] = None) -> Response:
    """Sends a DELETE request to `/files/{bucket}/{object}` endpoint to delete a file.

    Args:
        client: the authenticated client to be used to send the request to the API.
        bucket: the name of the bucket.
        path: the name of the object.
        version_id: the version id of the object. Optional.

    Returns:
        A `Response` object containing the response from the server.
    """
    endpoint = f"/api/v1/file/{workspace_name}/{path}"
    params = {"version_id": version_id} if version_id else {}
    response = client.delete(url=endpoint, params=params)
    
    if response.status_code == 200:
        response_obj = Response.from_httpx_response(response)
        return response_obj
    return handle_response_error(response)


def list_workspaces_me(
    client: httpx.Client,
) -> Response[Union[List[WorkspaceModel], ErrorMessage, HTTPValidationError]]:
    """Sends a GET request to `/api/v1/me/workspaces` endpoint to get the list of
    workspaces the current user has access to.

    Args:
        client: the authenticated Argilla client to be used to send the request to the API.

    Returns:
        A `Response` object containing a `parsed` attribute with the parsed response if
        the request was successful, which is a list of `WorkspaceModel`.
    """
    url = "/api/v1/me/workspaces"

    response = client.get(url=url)

    if response.status_code == 200:
        response_obj = Response.from_httpx_response(response)
        response_obj.parsed = [WorkspaceModel(**workspace) for workspace in response.json()["items"]]
        return response_obj
    return handle_response_error(response)
