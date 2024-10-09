from typing import TYPE_CHECKING
from argilla_server.contexts.files import get_pdf_s3_object_path, get_s3_object_url
from argilla_server.models.database import Document
import pytest
from httpx import AsyncClient
from unittest.mock import patch
from uuid import uuid4, UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from argilla_server.schemas.v1.documents import DocumentCreateRequest, DocumentDeleteRequest
from tests.factories import DocumentFactory, WorkspaceFactory

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_upload_document(async_client: "AsyncClient", db: "AsyncSession", owner_auth_header: dict):
    workspace = await WorkspaceFactory.create_with_s3(name="test-workspace")

    document_json = dict(
        id=str(uuid4()),
        reference="Test Document",
        pmid="123456",
        doi="10.1234/test.doi",
        file_name="test.pdf",
        workspace_id=str(workspace.id),
        # file_data="dGVzdCBmaWxlIGNvbnRlbnQ=",  # `test file content` in base64
    )

    upload_response = await async_client.post(
        "/api/v1/documents",
        params=document_json,
        files={"file_data": ("test.pdf", b"test file content", "application/pdf")},
        headers=owner_auth_header
    )

    assert upload_response.status_code == 201
    assert upload_response.json() == document_json['id']

    # Check if the document was created in the database with the correct URL
    result = await db.execute(select(Document))
    documents = result.scalars().all()
    assert [document.url for document in documents] == [
        get_s3_object_url(workspace.name, get_pdf_s3_object_path(document_json['id']))
    ]

    # Check if the file was uploaded to the S3 bucket
    get_response = await async_client.get(
        get_s3_object_url(workspace.name, get_pdf_s3_object_path(document_json['id']))
    )
    assert get_response.status_code == 200
    assert get_response.content == b"test file content"


@pytest.mark.asyncio
async def test_upload_duplicate_document(async_client: "AsyncClient", db: "AsyncSession", owner_auth_header: dict):
    workspace = await WorkspaceFactory.create_with_s3(name="test-workspace")

    existing_document = dict(
        id=str(uuid4()),
        reference="Test Document",
        pmid="123456",
        doi="10.1234/test.doi",
        file_name="test.pdf",
        workspace_id=str(workspace.id),
    )

    upload_response = await async_client.post(
        "/api/v1/documents",
        params=existing_document,
        files={"file_data": ("test.pdf", b"test file content", "application/pdf")},
        headers=owner_auth_header
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

    update_response = await async_client.post(
        "/api/v1/documents",
        params=update_document,
        files={"file_data": ("test.pdf", b"updated data", "application/pdf")},
        headers=owner_auth_header
    )

    # Ensure no new document was created in the database
    result = await db.execute(select(Document))
    documents = result.scalars().all()
    assert len(documents) == 1
    assert documents[0].pmid == "123456"

    # Check if the file was uploaded to the S3 bucket
    get_response = await async_client.get(
        get_s3_object_url(workspace.name, get_pdf_s3_object_path(update_document['id']))
    )
    assert get_response.status_code == 200
    assert get_response.content == b"updated data"

@pytest.mark.asyncio
async def test_get_document_by_pmid(async_client: "AsyncClient", db: "AsyncSession", owner_auth_header: dict):
    workspace = await WorkspaceFactory.create()
    document = await DocumentFactory.create(pmid="123456", workspace=workspace, workspace_id = workspace.id)

    response = await async_client.get(
        f"/api/v1/documents/by-pmid/{document.pmid}",
        headers=owner_auth_header
    )

    assert response.status_code == 200
    assert response.json()["pmid"] == document.pmid

@pytest.mark.asyncio
async def test_get_document_by_id(async_client: "AsyncClient", db: "AsyncSession", owner_auth_header: dict):
    document = await DocumentFactory.create()

    response = await async_client.get(
        f"/api/v1/documents/by-id/{document.id}",
        headers=owner_auth_header
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(document.id)

@pytest.mark.asyncio
async def test_delete_documents_by_id(async_client: "AsyncClient", db: "AsyncSession", owner_auth_header: dict):
    workspace = await WorkspaceFactory.create()
    document = await DocumentFactory.create(workspace=workspace)

    with patch("argilla_server.contexts.files.delete_object") as mock_delete_object:
        mock_delete_object.return_value = None

        document_delete = DocumentDeleteRequest(id=document.id)
        response = await async_client.delete(
            f"/api/v1/documents/workspace/{workspace.id}",
            params=document_delete.dict(),
            headers=owner_auth_header
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

    response = await async_client.get(
        f"/api/v1/documents/workspace/{workspace.id}",
        headers=owner_auth_header
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["id"] == str(document_a.id)