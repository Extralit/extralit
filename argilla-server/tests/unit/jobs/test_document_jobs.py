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
from unittest.mock import patch, MagicMock
from uuid import uuid4

from argilla_server.jobs.document_jobs import upload_document_job
from tests.factories import WorkspaceFactory, UserFactory


@pytest.mark.asyncio
class TestDocumentJobs:
    """Test suite for document job functions."""

    @patch("argilla_server.jobs.document_jobs.files")
    @patch("argilla_server.jobs.document_jobs.datasets")
    async def test_upload_document_job_success(self, mock_datasets, mock_files):
        """Test successful document upload job."""
        # Create test data
        workspace = await WorkspaceFactory.create()
        user = await UserFactory.create()
        document_id = uuid4()

        # Create document data
        document_data = {
            "id": str(document_id),
            "workspace_id": str(workspace.id),
            "reference": "test_ref",
            "doi": "10.1234/test.doi",
            "pmid": None,
            "url": None,
            "file_name": "test.pdf",
        }

        # Create file data
        file_data = b"%PDF-1.5 test pdf content"

        # Mock file operations
        mock_files.get_minio_client.return_value = MagicMock()
        mock_files.list_objects.return_value = MagicMock(objects=[])
        mock_files.get_pdf_s3_object_path.return_value = f"documents/{document_id}/test.pdf"

        # Mock S3 response
        mock_s3_response = MagicMock()
        mock_s3_response.bucket_name = workspace.name
        mock_s3_response.object_name = f"documents/{document_id}/test.pdf"
        mock_files.put_object.return_value = mock_s3_response
        mock_files.get_s3_object_url.return_value = f"s3://{workspace.name}/documents/{document_id}/test.pdf"

        # Mock document creation
        mock_document = MagicMock()
        mock_document.id = document_id
        mock_datasets.create_document.return_value = mock_document

        # Execute job
        result = await upload_document_job(document_data, file_data, str(user.id))

        # Verify result
        assert result["success"] is True
        assert result["id"] == str(document_id)
        assert result["status"] == "created"

        # Verify file operations
        mock_files.get_pdf_s3_object_path.assert_called_once_with(document_id)
        mock_files.put_object.assert_called_once()
        mock_files.get_s3_object_url.assert_called_once()

        # Verify document creation
        mock_datasets.create_document.assert_called_once()

    @patch("argilla_server.contexts.imports.check_existing_document")
    async def test_upload_document_job_existing_document(self, mock_check_existing):
        """Test document upload job with existing document."""
        # Create test data
        workspace = await WorkspaceFactory.create()
        user = await UserFactory.create()
        document_id = uuid4()

        # Create document data
        document_data = {
            "id": str(document_id),
            "workspace_id": str(workspace.id),
            "reference": "existing_ref",
            "doi": "10.1234/existing.doi",
            "pmid": None,
            "url": None,
            "file_name": "existing.pdf",
        }

        # Create file data
        file_data = b"%PDF-1.5 test pdf content"

        # Mock existing document
        mock_existing_document = MagicMock()
        mock_existing_document.id = document_id
        mock_check_existing.return_value = mock_existing_document

        # Execute job
        result = await upload_document_job(document_data, file_data, str(user.id))

        # Verify result
        assert result["success"] is True
        assert result["id"] == str(document_id)
        assert result["status"] == "existing"

        # Verify check_existing_document was called
        mock_check_existing.assert_called_once()

    @patch("argilla_server.jobs.document_jobs.Workspace")
    async def test_upload_document_job_workspace_not_found(self, mock_workspace_class):
        """Test document upload job with non-existent workspace."""
        # Create test data
        workspace_id = uuid4()
        user = await UserFactory.create()
        document_id = uuid4()

        # Create document data
        document_data = {
            "id": str(document_id),
            "workspace_id": str(workspace_id),
            "reference": "test_ref",
            "doi": "10.1234/test.doi",
            "pmid": None,
            "url": None,
            "file_name": "test.pdf",
        }

        # Create file data
        file_data = b"%PDF-1.5 test pdf content"

        # Mock workspace not found
        mock_workspace_class.get.return_value = None

        # Execute job
        result = await upload_document_job(document_data, file_data, str(user.id))

        # Verify result
        assert result["success"] is False
        assert "Workspace with id" in result["error"]
        assert "not found" in result["error"]

        # Verify workspace.get was called
        mock_workspace_class.get.assert_called_once_with(pytest.ANY, workspace_id)

    @patch("argilla_server.jobs.document_jobs.files")
    @patch("argilla_server.jobs.document_jobs.datasets")
    async def test_upload_document_job_exception(self, mock_datasets, mock_files):
        """Test document upload job with exception."""
        # Create test data
        workspace = await WorkspaceFactory.create()
        user = await UserFactory.create()
        document_id = uuid4()

        # Create document data
        document_data = {
            "id": str(document_id),
            "workspace_id": str(workspace.id),
            "reference": "test_ref",
            "doi": "10.1234/test.doi",
            "pmid": None,
            "url": None,
            "file_name": "test.pdf",
        }

        # Create file data
        file_data = b"%PDF-1.5 test pdf content"

        # Mock exception during file operations
        mock_files.get_minio_client.side_effect = Exception("Test exception")

        # Execute job
        result = await upload_document_job(document_data, file_data, str(user.id))

        # Verify result
        assert result["success"] is False
        assert "Test exception" in result["error"]
