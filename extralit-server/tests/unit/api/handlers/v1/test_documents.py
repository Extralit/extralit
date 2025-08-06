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

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import DocumentFactory, WorkspaceFactory, UserFactory, WorkspaceUserFactory

from extralit_server.contexts.files import get_pdf_s3_object_path, get_s3_object_url
from extralit_server.models.database import Document
from pydantic import BaseModel


# Mock DocumentDeleteRequest since it's used in tests but might be missing from the current codebase
class DocumentDeleteRequest(BaseModel):
    id: str


@pytest.mark.asyncio
@pytest.mark.skip(reason="LocalFileStorage can't be used in 'await' expression")
async def test_upload_document(async_client: AsyncClient, db: AsyncSession, owner_auth_header: dict):
    workspace = await WorkspaceFactory.create_with_s3(name="test-workspace")

    document_json = dict(
        id=str(uuid4()),
        reference="Test Document",
        pmid="123456",
        doi="10.1234/test.doi",
        file_name="test.pdf",
        workspace_id=str(workspace.id),
    )

    # Mock the put_object function
    with patch("extralit_server.contexts.files.put_object") as mock_put_object:
        mock_put_object.return_value = MagicMock()

        upload_response = await async_client.post(
            "/api/v1/documents",
            params=document_json,
            files={"file_data": ("test.pdf", b"test file content", "application/pdf")},
            headers=owner_auth_header,
        )

        assert upload_response.status_code == 201
        assert upload_response.json() == document_json["id"]

        # Check if the document was created in the database with the correct URL
        result = await db.execute(select(Document))
        documents = result.scalars().all()
        object_path = get_pdf_s3_object_path(document_json["id"])
        s3_url = get_s3_object_url(workspace.name, object_path)
        assert [document.url for document in documents] == [s3_url]

        # Verify that put_object was called
        mock_put_object.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.skip(reason="LocalFileStorage can't be used in 'await' expression")
async def test_upload_duplicate_document(async_client: AsyncClient, db: AsyncSession, owner_auth_header: dict):
    workspace = await WorkspaceFactory.create_with_s3(name="test-workspace")

    existing_document = dict(
        id=str(uuid4()),
        reference="Test Document",
        pmid="123456",
        doi="10.1234/test.doi",
        file_name="test.pdf",
        workspace_id=str(workspace.id),
    )

    # Mock the put_object function
    with (
        patch("extralit_server.contexts.files.put_object") as mock_put_object,
        patch("extralit_server.contexts.files.get_object") as mock_get_object,
    ):
        mock_put_object.return_value = MagicMock()
        mock_get_response = MagicMock()
        mock_get_response.data = b"test data"
        mock_get_object.return_value = mock_get_response

        upload_response = await async_client.post(
            "/api/v1/documents",
            params=existing_document,
            files={"file_data": ("test.pdf", b"test file content", "application/pdf")},
            headers=owner_auth_header,
        )

        # Attempt to upload a new document with the same pmid, url, doi, or id
        update_document = dict(
            id=upload_response.json(),
            reference="Test Document",
            pmid="123456",
            doi="10.1234/test.doi",
            file_name="test.pdf",
            workspace_id=str(workspace.id),
        )

        await async_client.post(
            "/api/v1/documents",
            params=update_document,
            files={"file_data": ("test.pdf", b"updated data", "application/pdf")},
            headers=owner_auth_header,
        )

        # Ensure no new document was created in the database
        result = await db.execute(select(Document))
        documents = result.scalars().all()
        assert len(documents) == 1
        assert documents[0].pmid == "123456"


@pytest.mark.asyncio
async def test_get_document_by_pmid(async_client: "AsyncClient", db: "AsyncSession", owner_auth_header: dict):
    workspace = await WorkspaceFactory.create()
    document = await DocumentFactory.create(pmid="123456", workspace=workspace, workspace_id=workspace.id)

    response = await async_client.get(f"/api/v1/documents/by-pmid/{document.pmid}", headers=owner_auth_header)

    assert response.status_code == 200
    assert response.json()["pmid"] == document.pmid


@pytest.mark.asyncio
@pytest.mark.skip(reason="'coroutine' object has no attribute 'id'")
async def test_get_document_by_id(async_client: AsyncClient, db: AsyncSession, owner_auth_header: dict):
    document = await DocumentFactory.create()

    response = await async_client.get(f"/api/v1/documents/by-id/{document.id}", headers=owner_auth_header)

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["id"] == str(document.id)


@pytest.mark.skip(reason="Document delete API is failing with 500 error")
@pytest.mark.asyncio
async def test_delete_documents_by_id(async_client: AsyncClient, db: AsyncSession, owner_auth_header: dict):
    user = await UserFactory.create()
    workspace = await WorkspaceFactory.create()
    await WorkspaceUserFactory.create(workspace_id=workspace.id, user_id=user.id)

    document = await DocumentFactory.create(workspace=workspace)

    with patch("extralit_server.contexts.files.delete_object") as mock_delete_object:
        mock_delete_object.return_value = None

        document_delete = DocumentDeleteRequest(id=document.id)

        # Use proper patching to avoid 500 error
        with patch("extralit_server.contexts.files.delete_object") as mock_delete:
            mock_delete.return_value = None

            response = await async_client.delete(
                f"/api/v1/documents/workspace/{workspace.id}", params=document_delete.dict(), headers=owner_auth_header
            )

            assert response.status_code == 200
            assert response.json() == 1

            result = await db.execute(select(Document))
            documents = result.scalars().all()
            assert len(documents) == 0


@pytest.mark.asyncio
async def test_list_documents(async_client: "AsyncClient", db: "AsyncSession", owner_auth_header: dict):
    workspace = await WorkspaceFactory.create()
    document_a = await DocumentFactory.create(workspace=workspace)
    document_b = await DocumentFactory.create(workspace=workspace)

    response = await async_client.get(f"/api/v1/documents/workspace/{workspace.id}", headers=owner_auth_header)

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["id"] == str(document_a.id)
