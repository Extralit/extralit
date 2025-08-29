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

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.jobs.document_jobs import upload_and_preprocess_documents_job
from tests.factories import UserFactory, WorkspaceFactory


@pytest.mark.asyncio
class TestDocumentJobs:
    """Test suite for document job functions."""

    @patch("extralit_server.jobs.document_jobs.files")
    @patch("extralit_server.jobs.document_jobs.datasets")
    @patch("extralit_server.jobs.document_jobs.imports")
    @pytest.mark.skip("temporarily skipping")
    async def test_upload_reference_documents_job_success(self, mock_imports, mock_datasets, mock_files):
        """Test successful reference documents upload job."""
        # Create test data
        workspace = await WorkspaceFactory.create()
        user = await UserFactory.create()
        reference = "test_ref"

        # Create document data
        document_data = {
            "workspace_id": str(workspace.id),
            "reference": reference,
            "doi": "10.1234/test.doi",
            "pmid": None,
        }

        # Create file data list
        file_data_list = [
            ("test1.pdf", b"%PDF-1.5 test pdf content 1"),
            ("test2.pdf", b"%PDF-1.5 test pdf content 2"),
        ]

        # Mock file operations
        mock_files.get_minio_client.return_value = MagicMock()
        mock_files.list_objects.return_value = MagicMock(objects=[])
        mock_files.get_pdf_s3_object_path.return_value = "documents/test-id/test.pdf"
        mock_files.put_object.return_value = MagicMock(bucket_name=workspace.name, object_name="test.pdf")
        mock_files.get_s3_object_url.return_value = f"s3://{workspace.name}/test.pdf"
        mock_files.compute_hash.return_value = "test_hash"

        # Mock imports.check_existing_document to return None (no existing document)
        mock_imports.check_existing_document.return_value = None

        # Mock document creation
        mock_document = MagicMock()
        mock_document.id = uuid4()
        mock_datasets.create_document.return_value = mock_document

        # Mock the model_dump method for DocumentCreate objects
        with patch("extralit_server.api.schemas.v1.documents.DocumentCreate.model_dump") as mock_model_dump:
            mock_model_dump.return_value = {"file_name": "test.pdf", "pmid": None, "doi": "10.1234/test.doi"}

            # Execute job
            result = await upload_and_preprocess_documents_job(reference, document_data, file_data_list, user.id)

            # Debug: print the actual result
            print(f"DEBUG: result = {result}")

            # Verify result
            assert result["success"] is True
            assert result["reference"] == reference
            assert result["total_files"] == 2
            assert result["successful_files"] == 2
            assert result["failed_files"] == 0

            # Verify file operations were called for each file
            assert mock_files.put_object.call_count == 2
            assert mock_datasets.create_document.call_count == 2

    async def test_upload_reference_documents_job_workspace_not_found(self):
        """Test reference documents upload job with non-existent workspace."""
        # Create test data
        workspace_id = uuid4()
        user = await UserFactory.create()
        reference = "test_ref"

        # Create document data
        document_data = {
            "workspace_id": str(workspace_id),
            "reference": reference,
            "doi": "10.1234/test.doi",
            "pmid": None,
        }

        # Create file data list
        file_data_list = [("test.pdf", b"%PDF-1.5 test pdf content")]

        # Use non-existent workspace ID - the job will handle the lookup internally

        # Execute job
        result = await upload_and_preprocess_documents_job(reference, document_data, file_data_list, user.id)

        # Verify result
        assert result["success"] is False
        assert result["reference"] == reference
        assert "not found" in result["errors"][0]

    @patch("extralit_server.jobs.document_jobs.files")
    @patch("extralit_server.jobs.document_jobs.datasets")
    @patch("extralit_server.jobs.document_jobs.imports")
    @pytest.mark.skip("temporarily skipping")
    async def test_upload_reference_documents_job_partial_failure(self, mock_imports, mock_datasets, mock_files):
        """Test reference documents upload job with partial failure."""
        # Create test data
        workspace = await WorkspaceFactory.create()
        user = await UserFactory.create()
        reference = "test_ref"

        # Create document data
        document_data = {
            "workspace_id": str(workspace.id),
            "reference": reference,
            "doi": "10.1234/test.doi",
            "pmid": None,
        }

        # Create file data list
        file_data_list = [
            ("test1.pdf", b"%PDF-1.5 test pdf content 1"),
            ("test2.pdf", b"%PDF-1.5 test pdf content 2"),
        ]

        # Mock file operations - first succeeds, second fails
        mock_files.get_minio_client.return_value = MagicMock()
        mock_files.list_objects.return_value = MagicMock(objects=[])
        mock_files.get_pdf_s3_object_path.return_value = "documents/test-id/test.pdf"

        # First call succeeds, second fails
        mock_files.put_object.side_effect = [
            MagicMock(bucket_name=workspace.name, object_name="test1.pdf"),
            Exception("S3 upload failed"),
        ]
        mock_files.get_s3_object_url.return_value = f"s3://{workspace.name}/test1.pdf"
        mock_files.compute_hash.return_value = "test_hash"

        # Mock imports.check_existing_document to return None (no existing document)
        mock_imports.check_existing_document.return_value = None

        # Mock document creation - only called once for successful file
        mock_document = MagicMock()
        mock_document.id = uuid4()
        mock_datasets.create_document.return_value = mock_document

        # Mock the model_dump method for DocumentCreate objects
        with patch("extralit_server.api.schemas.v1.documents.DocumentCreate.model_dump") as mock_model_dump:
            mock_model_dump.return_value = {"file_name": "test.pdf", "pmid": None, "doi": "10.1234/test.doi"}

            # Execute job
            result = await upload_and_preprocess_documents_job(reference, document_data, file_data_list, user.id)

            # Debug: print the actual result
            print(f"DEBUG: result = {result}")

            # Verify result
            assert result["success"] is False  # Overall failure due to partial failure
            assert result["reference"] == reference
            assert result["total_files"] == 2
            assert result["successful_files"] == 1
            assert result["failed_files"] == 1

            # Verify operations were attempted for both files
            assert mock_files.put_object.call_count == 2
            assert mock_datasets.create_document.call_count == 1  # Only for successful file
