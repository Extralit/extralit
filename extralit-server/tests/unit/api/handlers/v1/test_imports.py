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
from fastapi import status
from httpx import AsyncClient

from extralit_server.api.schemas.v1.documents import DocumentCreate
from extralit_server.api.schemas.v1.imports import (
    DocumentMetadata,
    FileInfo,
    ImportAnalysisRequest,
    ImportHistoryCreate,
    ImportStatus,
)
from extralit_server.models import UserRole
from tests.factories import DocumentFactory, UserFactory, WorkspaceFactory


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

    async def test_analyze_import_empty_documents(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test analyze endpoint with empty documents list."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        # Optionally assign workspaces to owner if needed by your logic
        # owner.workspaces = workspaces
        workspace = workspaces[0]

        # Create request with empty documents
        request = ImportAnalysisRequest(workspace_id=workspace.id, documents={})

        # Make request
        response = await async_client.post(
            "/api/v1/imports/analyze", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "No documents provided for analysis" in str(response.json())

    async def test_analyze_import_invalid_workspace(self, async_client: AsyncClient, owner_auth_header: dict):
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
        response = await async_client.post(
            "/api/v1/imports/analyze", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "not found" in response.json()["detail"]

    async def test_analyze_import_mismatched_workspace_ids(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test analyze endpoint with mismatched workspace IDs."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
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
        response = await async_client.post(
            "/api/v1/imports/analyze", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "mismatched workspace_id" in str(response.json())

    async def test_analyze_import_invalid_document_metadata(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test analyze endpoint with invalid document metadata - should not raise exceptions."""
        await UserFactory.create(role=UserRole.owner)
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
        response = await async_client.post(
            "/api/v1/imports/analyze", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response - should succeed but mark document as failed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "test_ref" in data["documents"]
        assert data["documents"]["test_ref"]["status"] == ImportStatus.FAILED
        assert data["summary"]["failed_count"] == 1

    async def test_analyze_import_new_documents(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test analyze endpoint with new documents."""
        await UserFactory.create(role=UserRole.owner)
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
        response = await async_client.post(
            "/api/v1/imports/analyze", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

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

    async def test_analyze_import_existing_documents(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test analyze endpoint with existing documents."""
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create existing document
        await DocumentFactory.create(workspace=workspace, reference="existing_ref", doi="10.1234/existing.doi")

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
                    associated_files=[
                        FileInfo(filename="existing.pdf", size=1024)
                    ],  # Add file to avoid validation failure
                )
            },
        )

        # Make request
        response = await async_client.post(
            "/api/v1/imports/analyze", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "existing_ref" in data["documents"]
        assert data["documents"]["existing_ref"]["status"] == ImportStatus.UPDATE
        assert data["summary"]["add_count"] == 0
        assert data["summary"]["update_count"] == 1
        assert data["summary"]["skip_count"] == 0
        assert data["summary"]["failed_count"] == 0

    async def test_analyze_import_update_documents(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test analyze endpoint with documents that need updates."""
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create existing document
        await DocumentFactory.create(workspace=workspace, reference="update_ref", doi="10.1234/update.doi")

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
        response = await async_client.post(
            "/api/v1/imports/analyze", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

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

    async def test_analyze_import_mixed_documents(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test analyze endpoint with mixed document types."""
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create existing documents
        await DocumentFactory.create(workspace=workspace, reference="skip_ref", doi="10.1234/skip.doi")
        await DocumentFactory.create(workspace=workspace, reference="update_ref", doi="10.1234/update.doi")

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
                    associated_files=[FileInfo(filename="skip.pdf", size=1024)],  # Add file to avoid validation failure
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
        response = await async_client.post(
            "/api/v1/imports/analyze", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response - should succeed with mixed statuses
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check document statuses
        assert data["documents"]["new_ref"]["status"] == ImportStatus.ADD
        assert data["documents"]["skip_ref"]["status"] == ImportStatus.UPDATE
        assert data["documents"]["update_ref"]["status"] == ImportStatus.UPDATE
        assert data["documents"]["failed_ref"]["status"] == ImportStatus.FAILED

        # Check summary counts
        assert data["summary"]["add_count"] == 1
        assert data["summary"]["update_count"] == 2
        assert data["summary"]["skip_count"] == 0
        assert data["summary"]["failed_count"] == 1

    async def test_create_import_history_unauthorized(self, async_client: AsyncClient):
        """Test that unauthorized users cannot access the import history endpoint."""
        # Create a request with a valid workspace ID
        request = ImportHistoryCreate(
            workspace_id=uuid4(),
            filename="test.bib",
            data={"schema": {"fields": [], "primaryKey": []}, "data": []},
        )

        # Make request without authentication
        response = await async_client.post("/api/v1/imports/history", json=request.model_dump(mode="json"))

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_import_history_invalid_workspace(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test import history endpoint with invalid workspace ID."""
        # Create request with non-existent workspace ID
        request = ImportHistoryCreate(
            workspace_id=uuid4(),
            filename="test.bib",
            data={"schema": {"fields": [], "primaryKey": []}, "data": []},
        )

        # Make request
        response = await async_client.post(
            "/api/v1/imports/history", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "not found" in response.json()["detail"]

    async def test_create_import_history_invalid_data(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test import history endpoint with invalid data structure."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create request with invalid data structure
        request = ImportHistoryCreate(
            workspace_id=workspace.id,
            filename="test.bib",
            data={"invalid": "structure"},  # Missing schema and data fields
        )

        # Make request
        response = await async_client.post(
            "/api/v1/imports/history", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_detail = response.json()["detail"]
        assert "Data must contain 'data' field" in str(error_detail)

    async def test_create_import_history_empty_filename(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test import history endpoint with empty filename."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create request with empty filename
        request = ImportHistoryCreate(
            workspace_id=workspace.id,
            filename="",
            data={"schema": {"fields": [], "primaryKey": []}, "data": []},
        )

        # Make request
        response = await async_client.post(
            "/api/v1/imports/history", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Filename cannot be empty" in str(response.json())

    async def test_create_import_history_invalid_metadata(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test import history endpoint with invalid metadata structure."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create request with invalid metadata
        request = ImportHistoryCreate(
            workspace_id=workspace.id,
            filename="test.bib",
            data={"schema": {"fields": [], "primaryKey": []}, "data": []},
            metadata={
                "ref1": {
                    "status": "invalid_status",  # Invalid status
                    "associated_files": "not_a_list",  # Should be a list
                },
                "ref2": "not_a_dict",  # Should be a dictionary
            },
        )

        # Make request
        response = await async_client.post(
            "/api/v1/imports/history", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_detail = response.json()["detail"]
        assert "Invalid status 'invalid_status'" in str(error_detail)
        assert "Associated files for reference 'ref1' must be a list" in str(error_detail)
        assert "Metadata for reference 'ref2' must be a dictionary" in str(error_detail)

    async def test_create_import_history_success(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test successful import history creation."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create valid dataframe data
        dataframe_data = {
            "schema": {
                "fields": [
                    {"name": "reference", "type": "string"},
                    {"name": "title", "type": "string"},
                    {"name": "authors", "type": "string"},
                    {"name": "year", "type": "integer"},
                    {"name": "doi", "type": "string"},
                ],
                "primaryKey": ["reference"],
            },
            "data": [
                {
                    "reference": "Smith2024",
                    "title": "Test Paper",
                    "authors": "John Smith",
                    "year": 2024,
                    "doi": "10.1234/test.doi",
                },
                {
                    "reference": "Doe2023",
                    "title": "Another Paper",
                    "authors": "Jane Doe",
                    "year": 2023,
                    "doi": "10.5678/another.doi",
                },
            ],
        }

        # Create metadata with import status and associated files
        metadata = {
            "Smith2024": {"status": "add", "associated_files": ["smith2024.pdf"]},
            "Doe2023": {"status": "update", "associated_files": ["doe2023.pdf", "doe2023_supplement.pdf"]},
        }

        # Create request
        request = ImportHistoryCreate(
            workspace_id=workspace.id,
            filename="test_import.bib",
            data=dataframe_data,
            metadata=metadata,
        )

        # Make request
        response = await async_client.post(
            "/api/v1/imports/history", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["workspace_id"] == str(workspace.id)
        assert data["filename"] == "test_import.bib"
        assert "created_at" in data

    async def test_create_import_history_bibtex_data(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test import history creation with BibTeX-style dataframe data."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create BibTeX-style dataframe data
        bibtex_dataframe = {
            "schema": {
                "fields": [
                    {"name": "reference", "type": "string"},
                    {"name": "title", "type": "string"},
                    {"name": "authors", "type": "string"},
                    {"name": "year", "type": "integer"},
                    {"name": "venue", "type": "string"},
                    {"name": "doi", "type": "string"},
                    {"name": "pmid", "type": "string"},
                    {"name": "file_name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "associated_files", "type": "string"},
                ],
                "primaryKey": ["reference"],
            },
            "data": [
                {
                    "reference": "Hawley2003a",
                    "title": "Community-wide effects of permethrin-treated bed nets",
                    "authors": "William A Hawley, Penelope A Phillips-Howard",
                    "year": 2003,
                    "venue": "The American Journal of Tropical Medicine and Hygiene",
                    "doi": "",
                    "pmid": "12749495",
                    "file_name": "hawley2003.pdf",
                    "status": "add",
                    "associated_files": "hawley2003.pdf",
                },
                {
                    "reference": "PMI2019",
                    "title": "Durability Monitoring of LLINs in Zanzibar, Tanzania",
                    "authors": "PMI",
                    "year": 2019,
                    "venue": "",
                    "doi": "",
                    "pmid": "",
                    "file_name": "pmi2019.pdf",
                    "status": "add",
                    "associated_files": "pmi2019.pdf",
                },
            ],
        }

        # Create metadata with import status and associated files for each reference
        bibtex_metadata = {
            "Hawley2003a": {"status": "add", "associated_files": ["hawley2003.pdf"]},
            "PMI2019": {"status": "add", "associated_files": ["pmi2019.pdf"]},
        }

        # Create request
        request = ImportHistoryCreate(
            workspace_id=workspace.id,
            filename="zotero_export.bib",
            data=bibtex_dataframe,
            metadata=bibtex_metadata,
        )

        # Make request
        response = await async_client.post(
            "/api/v1/imports/history", headers=owner_auth_header, json=request.model_dump(mode="json")
        )

        # Verify response
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["workspace_id"] == str(workspace.id)
        assert data["filename"] == "zotero_export.bib"
        assert "created_at" in data

    async def test_list_import_histories_unauthorized(self, async_client: AsyncClient):
        """Test that unauthorized users cannot access the list import histories endpoint."""
        # Make request without authentication
        response = await async_client.get(f"/api/v1/imports/history?workspace_id={uuid4()}")

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_list_import_histories_invalid_workspace(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test list import histories endpoint with invalid workspace ID."""
        # Make request with non-existent workspace ID
        response = await async_client.get(f"/api/v1/imports/history?workspace_id={uuid4()}", headers=owner_auth_header)

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "not found" in response.json()["detail"]

    async def test_list_import_histories_empty(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test list import histories endpoint with no import histories."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Make request
        response = await async_client.get(
            f"/api/v1/imports/history?workspace_id={workspace.id}", headers=owner_auth_header
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_import_histories_with_limit(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test list import histories endpoint with limit parameter for Recent Imports sidebar."""
        # Create owner user and workspace
        await UserFactory.create(role=UserRole.owner)
        workspaces = await WorkspaceFactory.create_batch(1)
        workspace = workspaces[0]

        # Create multiple import history records
        import_requests = []
        for i in range(10):
            dataframe_data = {
                "schema": {
                    "fields": [
                        {"name": "reference", "type": "string"},
                        {"name": "title", "type": "string"},
                    ],
                    "primaryKey": ["reference"],
                },
                "data": [
                    {
                        "reference": f"ref{i}",
                        "title": f"Test Paper {i}",
                    }
                ],
            }

            request = ImportHistoryCreate(
                workspace_id=workspace.id,
                filename=f"test_import_{i}.bib",
                data=dataframe_data,
                metadata={f"ref{i}": {"status": "add", "associated_files": [f"test{i}.pdf"]}},
            )
            import_requests.append(request)

        # Create all import history records
        for request in import_requests:
            response = await async_client.post(
                "/api/v1/imports/history", headers=owner_auth_header, json=request.model_dump(mode="json")
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Test without limit - should return all records
        response = await async_client.get(
            f"/api/v1/imports/history?workspace_id={workspace.id}", headers=owner_auth_header
        )
        assert response.status_code == status.HTTP_200_OK
        all_data = response.json()
        assert len(all_data) == 10

        # Test with limit=5 - should return only 5 most recent records
        response = await async_client.get(
            f"/api/v1/imports/history?workspace_id={workspace.id}&limit=5", headers=owner_auth_header
        )
        assert response.status_code == status.HTTP_200_OK
        limited_data = response.json()
        assert len(limited_data) == 5

        # Verify that the returned records are the most recent ones (ordered by created_at desc)
        # The most recent should be test_import_9.bib, test_import_8.bib, etc.
        filenames = [record["filename"] for record in limited_data]
        expected_filenames = [f"test_import_{i}.bib" for i in range(9, 4, -1)]  # 9, 8, 7, 6, 5
        assert filenames == expected_filenames

        # Test with limit=3 - should return only 3 most recent records
        response = await async_client.get(
            f"/api/v1/imports/history?workspace_id={workspace.id}&limit=3", headers=owner_auth_header
        )
        assert response.status_code == status.HTTP_200_OK
        limited_data = response.json()
        assert len(limited_data) == 3

        # Test with limit=0 - should return empty list
        response = await async_client.get(
            f"/api/v1/imports/history?workspace_id={workspace.id}&limit=0", headers=owner_auth_header
        )
        assert response.status_code == status.HTTP_200_OK
        limited_data = response.json()
        assert len(limited_data) == 0

        # Verify that list view doesn't include data field (only metadata)
        for record in all_data:
            assert "id" in record
            assert "workspace_id" in record
            assert "filename" in record
            assert "created_at" in record
            assert "metadata" in record
