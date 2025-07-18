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
from uuid import uuid4
from fastapi import status
from httpx import AsyncClient

from argilla_server.api.schemas.v1.documents import DocumentCreate
from argilla_server.api.schemas.v1.imports import (
    FileInfo,
    DocumentMetadata,
    ImportAnalysisRequest,
    ImportStatus,
)

from argilla_server.models import UserRole
from tests.factories import DocumentFactory, WorkspaceFactory, UserFactory


@pytest.mark.asyncio
class TestImportsAPI:
    """Test suite for imports API endpoints."""

    async def test_analyze_import_unauthorized(self, async_client: AsyncClient):
        """Test that unauthorized users cannot access the analyze endpoint."""
        # Create a request with a valid workspace ID
        request = ImportAnalysisRequest(workspace_id=uuid4(), documents={})

        # Make request without authentication
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_analyze_import_empty_documents(self, async_client: AsyncClient):
        """Test analyze endpoint with empty documents list."""
        # Create owner user and workspace
        owner = await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        # Optionally assign workspaces to owner if needed by your logic
        # owner.workspaces = workspaces
        workspace = workspaces[0]

        # Create request with empty documents
        request = ImportAnalysisRequest(workspace_id=workspace.id, documents={})

        # Make request
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "No documents provided for analysis" in str(response.json())

    async def test_analyze_import_invalid_workspace(self, async_client: AsyncClient):
        """Test analyze endpoint with invalid workspace ID."""
        # Create request with non-existent workspace ID
        request = ImportAnalysisRequest(
            workspace_id=uuid4(),
            documents={
                "test_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=uuid4(), reference="test_ref", url=None, file_name=None, pmid=None, doi=None
                    ),
                    title="Test Document",
                    authors=["Test Author"],
                    year=None,
                    venue=None,
                )
            },
        )

        # Make request
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "not found" in response.json()["detail"]

    async def test_analyze_import_mismatched_workspace_ids(self, async_client: AsyncClient):
        """Test analyze endpoint with mismatched workspace IDs."""
        # Create owner user and workspace
        owner = await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]
        other_workspace_id = uuid4()

        # Create request with mismatched workspace IDs
        request = ImportAnalysisRequest(
            workspace_id=workspace.id,
            documents={
                "test_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=other_workspace_id,
                        reference="test_ref",
                        url=None,
                        file_name=None,
                        pmid=None,
                        doi=None,
                    ),
                    title="Test Document",
                    authors=["Test Author"],
                    year=None,
                    venue=None,
                )
            },
        )

        # Make request
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "mismatched workspace_id" in str(response.json())

    async def test_analyze_import_invalid_document_metadata(self, async_client: AsyncClient):
        """Test analyze endpoint with invalid document metadata - should not raise exceptions."""
        owner = await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create request with invalid DOI format
        request = ImportAnalysisRequest(
            workspace_id=workspace.id,
            documents={
                "test_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=workspace.id,
                        reference="test_ref",
                        doi="invalid-doi-format",  # Invalid DOI format
                        url=None,
                        file_name=None,
                        pmid=None,
                    ),
                    title="Test Document",
                    authors=["Test Author"],
                    year=None,
                    venue=None,
                    associated_files=[FileInfo(filename="test.pdf", size=1024)],
                )
            },
        )

        # Make request
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response - should succeed but mark document as failed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "test_ref" in data["documents"]
        assert data["documents"]["test_ref"]["status"] == ImportStatus.FAILED
        assert data["summary"]["failed_count"] == 1

    async def test_analyze_import_new_documents(self, async_client: AsyncClient):
        """Test analyze endpoint with new documents."""
        owner = await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create request with new document
        request = ImportAnalysisRequest(
            workspace_id=workspace.id,
            documents={
                "new_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=workspace.id,
                        reference="new_ref",
                        doi="10.1234/new.doi",
                        url=None,
                        file_name=None,
                        pmid=None,
                    ),
                    title="New Document",
                    authors=["New Author"],
                    year=2024,
                    venue="Test Journal",
                    associated_files=[FileInfo(filename="new_document.pdf", size=1024000)],
                )
            },
        )

        # Make request
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "new_ref" in data["documents"]
        assert data["documents"]["new_ref"]["status"] == ImportStatus.ADD
        assert data["summary"]["add_count"] == 1
        assert data["summary"]["update_count"] == 0
        assert data["summary"]["skip_count"] == 0
        assert data["summary"]["failed_count"] == 0

    async def test_analyze_import_existing_documents(self, async_client: AsyncClient):
        """Test analyze endpoint with existing documents."""
        owner = await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create existing document
        existing_doc = await DocumentFactory.create(
            workspace=workspace, reference="existing_ref", doi="10.1234/existing.doi"
        )

        # Create request with existing document
        request = ImportAnalysisRequest(
            workspace_id=workspace.id,
            documents={
                "existing_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=workspace.id,
                        reference="existing_ref",
                        doi="10.1234/existing.doi",
                        url=None,
                        file_name=None,
                        pmid=None,
                    ),
                    title="Existing Document",
                    authors=["Existing Author"],
                    year=2023,
                    venue="Existing Journal",
                    associated_files=[],  # No new files
                )
            },
        )

        # Make request
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "existing_ref" in data["documents"]
        assert data["documents"]["existing_ref"]["status"] == ImportStatus.SKIP
        assert data["summary"]["add_count"] == 0
        assert data["summary"]["update_count"] == 0
        assert data["summary"]["skip_count"] == 1
        assert data["summary"]["failed_count"] == 0

    async def test_analyze_import_update_documents(self, async_client: AsyncClient):
        """Test analyze endpoint with documents that need updates."""
        owner = await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create existing document
        existing_doc = await DocumentFactory.create(
            workspace=workspace, reference="update_ref", doi="10.1234/update.doi"
        )

        # Create request with document that needs update
        request = ImportAnalysisRequest(
            workspace_id=workspace.id,
            documents={
                "update_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=workspace.id,
                        reference="update_ref",
                        doi="10.1234/update.doi",
                        url=None,
                        file_name=None,
                        pmid=None,
                    ),
                    title="Update Document",
                    authors=["Update Author"],
                    year=2024,
                    venue="Update Journal",
                    associated_files=[FileInfo(filename="updated_document.pdf", size=2048000)],
                )
            },
        )

        # Make request
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "update_ref" in data["documents"]
        assert data["documents"]["update_ref"]["status"] == ImportStatus.UPDATE
        assert data["summary"]["add_count"] == 0
        assert data["summary"]["update_count"] == 1
        assert data["summary"]["skip_count"] == 0
        assert data["summary"]["failed_count"] == 0

    async def test_analyze_import_mixed_documents(self, async_client: AsyncClient):
        """Test analyze endpoint with mixed document types."""
        owner = await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create existing documents
        existing_skip = await DocumentFactory.create(workspace=workspace, reference="skip_ref", doi="10.1234/skip.doi")
        existing_update = await DocumentFactory.create(
            workspace=workspace, reference="update_ref", doi="10.1234/update.doi"
        )

        # Create request with mixed documents
        request = ImportAnalysisRequest(
            workspace_id=workspace.id,
            documents={
                "new_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=workspace.id,
                        reference="new_ref",
                        doi="10.1234/new.doi",
                        url=None,
                        file_name=None,
                        pmid=None,
                    ),
                    title="New Document",
                    authors=["New Author"],
                    year=2024,
                    venue="New Journal",
                    associated_files=[FileInfo(filename="new.pdf", size=1024)],
                ),
                "skip_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=workspace.id,
                        reference="skip_ref",
                        doi="10.1234/skip.doi",
                        url=None,
                        file_name=None,
                        pmid=None,
                    ),
                    title="Skip Document",
                    authors=["Skip Author"],
                    year=2023,
                    venue="Skip Journal",
                    associated_files=[],  # No new files
                ),
                "update_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=workspace.id,
                        reference="update_ref",
                        doi="10.1234/update.doi",
                        url=None,
                        file_name=None,
                        pmid=None,
                    ),
                    title="Update Document",
                    authors=["Update Author"],
                    year=2024,
                    venue="Update Journal",
                    associated_files=[FileInfo(filename="update.pdf", size=2048)],
                ),
                "failed_ref": DocumentMetadata(
                    document_create=DocumentCreate(
                        workspace_id=workspace.id,
                        reference="failed_ref",
                        doi="invalid-doi-format",  # Invalid DOI format
                        url=None,
                        file_name=None,
                        pmid=None,
                    ),
                    title="Failed Document",
                    authors=["Failed Author"],
                    year=2024,
                    venue="Failed Journal",
                    associated_files=[FileInfo(filename="failed.pdf", size=1024)],
                ),
            },
        )

        # Make request
        response = await async_client.post("/api/v1/imports/analyze", json=request.model_dump(mode="json"))

        # Verify response - should succeed with mixed statuses
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check document statuses
        assert data["documents"]["new_ref"]["status"] == ImportStatus.ADD
        assert data["documents"]["skip_ref"]["status"] == ImportStatus.SKIP
        assert data["documents"]["update_ref"]["status"] == ImportStatus.UPDATE
        assert data["documents"]["failed_ref"]["status"] == ImportStatus.FAILED

        # Check summary counts
        assert data["summary"]["add_count"] == 1
        assert data["summary"]["update_count"] == 1
        assert data["summary"]["skip_count"] == 1
        assert data["summary"]["failed_count"] == 1
