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
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.documents import DocumentCreate
from extralit_server.api.schemas.v1.imports import (
    DocumentMetadata,
    FileInfo,
    ImportAnalysisRequest,
    ImportStatus,
)
from extralit_server.contexts.imports import (
    analyze_import_status,
    validate_document_metadata,
)
from tests.factories import DocumentFactory, WorkspaceFactory


@pytest.mark.asyncio
class TestImportAnalysis:
    """Test suite for import analysis logic."""

    async def test_analyze_import_status_new_documents(self, db: AsyncSession):
        """Test analysis of new documents that should be added."""
        workspace = await WorkspaceFactory.create()

        # Create request with new documents
        document_create = DocumentCreate(
            workspace_id=workspace.id,
            reference="new_ref_1",
            doi="10.1234/new.doi.1",
            pmid="12345",
            file_name="new_document.pdf",
        )

        file_metadata = DocumentMetadata(
            document_create=document_create,
            title="New Document Title",
            authors=["Author One", "Author Two"],
            year=2024,
            venue="Test Journal",
            associated_files=[FileInfo(filename="new_document.pdf", size=1024000)],
        )

        request = ImportAnalysisRequest(workspace_id=workspace.id, documents={"new_ref_1": file_metadata})

        # Analyze import status
        response = await analyze_import_status(db, request)

        # Verify results
        assert len(response.documents) == 1
        assert "new_ref_1" in response.documents

        doc_info = response.documents["new_ref_1"]
        assert doc_info.status == ImportStatus.ADD
        # Note: DocumentImportAnalysis doesn't include title, authors, year, venue
        # These are stored in the dataframe structure in the response
        assert doc_info.document_create.reference == "new_ref_1"
        assert doc_info.document_create.doi == "10.1234/new.doi.1"
        assert doc_info.associated_files == ["new_document.pdf"]

        # Verify summary
        assert response.summary.total_documents == 1
        assert response.summary.add_count == 1
        assert response.summary.update_count == 0
        assert response.summary.skip_count == 0
        assert response.summary.failed_count == 0

    async def test_analyze_import_status_existing_documents_skip(self, db: AsyncSession):
        """Test analysis of existing documents that should be skipped."""
        workspace = await WorkspaceFactory.create()

        # Create existing document with same file name as the new import
        await DocumentFactory.create(
            workspace=workspace,
            reference="existing_ref",
            doi="10.1234/existing.doi",
            pmid="67890",
            file_name="existing_document.pdf",  # Same file name as the new import
        )

        # Create request with same document
        document_create = DocumentCreate(
            workspace_id=workspace.id,
            reference="existing_ref",
            doi="10.1234/existing.doi",
            pmid="67890",
            file_name="existing_document.pdf",
        )

        file_metadata = DocumentMetadata(
            document_create=document_create,
            title="Existing Document Title",
            authors=["Existing Author"],
            year=2023,
            venue="Existing Journal",
            associated_files=[
                FileInfo(filename="existing_document.pdf", size=1024)
            ],  # Add file to avoid validation failure
        )

        request = ImportAnalysisRequest(workspace_id=workspace.id, documents={"existing_ref": file_metadata})

        # Analyze import status
        response = await analyze_import_status(db, request)

        # Verify results
        assert len(response.documents) == 1
        doc_info = response.documents["existing_ref"]
        assert doc_info.status == ImportStatus.SKIP

        # Verify summary
        assert response.summary.skip_count == 1
        assert response.summary.add_count == 0

    async def test_analyze_import_status_existing_documents_update(self, db: AsyncSession):
        """Test analysis of existing documents that should be updated."""
        workspace = await WorkspaceFactory.create()

        # Create existing document
        await DocumentFactory.create(workspace=workspace, reference="update_ref", doi="10.1234/update.doi")

        # Create request with same document but new files
        document_create = DocumentCreate(
            workspace_id=workspace.id,
            reference="update_ref",
            doi="10.1234/update.doi",
            file_name="updated_document.pdf",
        )

        file_metadata = DocumentMetadata(
            document_create=document_create,
            title="Updated Document Title",
            authors=["Updated Author"],
            year=2024,
            venue="Updated Journal",
            associated_files=[FileInfo(filename="updated_document.pdf", size=2048000)],
        )

        request = ImportAnalysisRequest(workspace_id=workspace.id, documents={"update_ref": file_metadata})

        # Analyze import status
        response = await analyze_import_status(db, request)

        # Verify results
        assert len(response.documents) == 1
        doc_info = response.documents["update_ref"]
        assert doc_info.status == ImportStatus.UPDATE

        # Verify summary
        assert response.summary.update_count == 1

    async def test_analyze_import_status_failed_validation(self, db: AsyncSession):
        """Test analysis of documents that fail validation."""
        workspace = await WorkspaceFactory.create()

        # Create request with invalid document (invalid DOI format)
        document_create = DocumentCreate(
            workspace_id=workspace.id,
            reference="invalid_ref",
            doi="invalid-doi-format",  # Invalid DOI format
        )

        file_metadata = DocumentMetadata(
            document_create=document_create,
            title="Invalid Document",
            authors=["Invalid Author"],
            year=2024,
            venue="Invalid Journal",
            associated_files=[],
        )

        request = ImportAnalysisRequest(workspace_id=workspace.id, documents={"invalid_ref": file_metadata})

        # Analyze import status
        response = await analyze_import_status(db, request)

        # Verify results
        assert len(response.documents) == 1
        doc_info = response.documents["invalid_ref"]
        assert doc_info.status == ImportStatus.FAILED

        # Verify summary
        assert response.summary.failed_count == 1

    async def test_analyze_import_status_mixed_documents(self, db: AsyncSession):
        """Test analysis of mixed document types (add, update, skip, failed)."""
        workspace = await WorkspaceFactory.create()

        # Create existing document for skip test - with same file name
        await DocumentFactory.create(
            workspace=workspace,
            reference="skip_ref",
            doi="10.1234/skip.doi",
            file_name="skip.pdf",  # Same file name as the new import
        )

        # Create existing document for update test
        await DocumentFactory.create(workspace=workspace, reference="update_ref", doi="10.1234/update.doi")

        # Prepare mixed documents
        documents = {
            "new_ref": DocumentMetadata(
                document_create=DocumentCreate(workspace_id=workspace.id, reference="new_ref", doi="10.1234/new.doi"),
                title="New Document",
                authors=["New Author"],
                year=2024,
                venue="New Journal",
                associated_files=[FileInfo(filename="new.pdf", size=1024)],
            ),
            "skip_ref": DocumentMetadata(
                document_create=DocumentCreate(workspace_id=workspace.id, reference="skip_ref", doi="10.1234/skip.doi"),
                title="Skip Document",
                authors=["Skip Author"],
                year=2023,
                venue="Skip Journal",
                associated_files=[FileInfo(filename="skip.pdf", size=1024)],  # Same file name as existing
            ),
            "update_ref": DocumentMetadata(
                document_create=DocumentCreate(
                    workspace_id=workspace.id, reference="update_ref", doi="10.1234/update.doi"
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
                ),
                title="Failed Document",
                authors=["Failed Author"],
                year=2024,
                venue="Failed Journal",
                associated_files=[FileInfo(filename="failed.pdf", size=1024)],
            ),
        }

        request = ImportAnalysisRequest(workspace_id=workspace.id, documents=documents)

        # Analyze import status
        response = await analyze_import_status(db, request)

        # Verify results
        assert len(response.documents) == 4
        assert response.documents["new_ref"].status == ImportStatus.ADD
        assert response.documents["skip_ref"].status == ImportStatus.SKIP
        assert response.documents["update_ref"].status == ImportStatus.UPDATE
        assert response.documents["failed_ref"].status == ImportStatus.FAILED

        # Verify summary
        assert response.summary.total_documents == 4
        assert response.summary.add_count == 1
        assert response.summary.update_count == 1
        assert response.summary.skip_count == 1
        assert response.summary.failed_count == 1


class TestValidateDocumentMetadata:
    """Test suite for document metadata validation."""

    def test_validate_document_metadata_valid(self):
        """Test validation of valid document metadata."""
        document_create = DocumentCreate(
            workspace_id=uuid4(), reference="valid_ref", doi="10.1234/valid.doi", pmid="12345", file_name="valid.pdf"
        )
        file_metadata = DocumentMetadata(
            document_create=document_create,
            title="Valid Doc",
            associated_files=[FileInfo(filename="valid.pdf", size=1024)],
        )
        errors = validate_document_metadata(file_metadata)
        assert len(errors) == 0

    def test_validate_document_metadata_missing_workspace_id(self):
        """Test validation when workspace_id is missing."""
        # Create a valid document first
        document_create = DocumentCreate(workspace_id=uuid4(), reference="test_ref")
        document_create.__dict__["workspace_id"] = None
        file_metadata = DocumentMetadata(document_create=document_create, title="Test Doc")
        errors = validate_document_metadata(file_metadata)
        assert "workspace_id is required" in errors

    def test_validate_document_metadata_no_identifiers(self):
        """Test validation when no identifiers are provided."""
        document_create = DocumentCreate(workspace_id=uuid4())
        file_metadata = DocumentMetadata(document_create=document_create, title="No ID Doc")
        errors = validate_document_metadata(file_metadata)
        assert any("At least one identifier" in error for error in errors)

    def test_validate_document_metadata_invalid_doi(self):
        """Test validation of invalid DOI format."""
        document_create = DocumentCreate(workspace_id=uuid4(), doi="invalid-doi-format")
        file_metadata = DocumentMetadata(document_create=document_create, title="Invalid DOI Doc")
        errors = validate_document_metadata(file_metadata)
        assert any("Invalid DOI format" in error for error in errors)

    def test_validate_document_metadata_valid_doi(self):
        """Test validation of valid DOI format."""
        document_create = DocumentCreate(workspace_id=uuid4(), doi="10.1234/valid.doi")
        file_metadata = DocumentMetadata(document_create=document_create, title="Valid DOI Doc")
        errors = validate_document_metadata(file_metadata)
        doi_errors = [error for error in errors if "DOI format" in error]
        assert len(doi_errors) == 0

    def test_validate_document_metadata_invalid_pmid(self):
        """Test validation of invalid PMID format."""
        document_create = DocumentCreate(workspace_id=uuid4(), pmid="invalid-pmid")
        file_metadata = DocumentMetadata(document_create=document_create, title="Invalid PMID Doc")
        errors = validate_document_metadata(file_metadata)
        assert any("Invalid PMID format" in error for error in errors)

    def test_validate_document_metadata_valid_pmid(self):
        """Test validation of valid PMID format."""
        document_create = DocumentCreate(workspace_id=uuid4(), pmid="12345678")
        file_metadata = DocumentMetadata(document_create=document_create, title="Valid PMID Doc")
        errors = validate_document_metadata(file_metadata)
        pmid_errors = [error for error in errors if "PMID format" in error]
        assert len(pmid_errors) == 0

    def test_validate_document_metadata_multiple_errors(self):
        """Test validation with multiple errors."""
        # Create a valid document first
        document_create = DocumentCreate(workspace_id=uuid4(), doi="invalid-doi", pmid="invalid-pmid")
        document_create.__dict__["workspace_id"] = None
        file_metadata = DocumentMetadata(document_create=document_create, title="Multi Error Doc")
        errors = validate_document_metadata(file_metadata)
        assert len(errors) >= 3  # workspace_id, doi, pmid errors
        assert "workspace_id is required" in errors
        assert any("Invalid DOI format" in error for error in errors)
        assert any("Invalid PMID format" in error for error in errors)
