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

import json
import pytest
from io import BytesIO
from uuid import uuid4
from unittest.mock import patch, MagicMock
from fastapi import status
from httpx import AsyncClient

from argilla_server.models import UserRole
from tests.factories import WorkspaceFactory, UserFactory


@pytest.mark.asyncio
class TestBulkDocumentsAPI:
    """Test suite for bulk documents API endpoints."""

    @patch("argilla_server.api.handlers.v1.documents.upload_document_job")
    async def test_bulk_upload_documents_unauthorized(self, mock_job, async_client: AsyncClient):
        """Test that unauthorized users cannot access the bulk upload endpoint."""
        # Create a simple request
        documents_metadata = {
            "documents": [
                {
                    "reference_key": "test_ref",
                    "document_create": {
                        "workspace_id": str(uuid4()),
                        "reference": "test_ref",
                    },
                    "associated_file": "test.pdf",
                }
            ]
        }

        # Create a test PDF file
        test_pdf = BytesIO(b"%PDF-1.5 test pdf content")

        # Make request without authentication
        response = await async_client.post(
            "/documents/bulk",
            files={
                "documents_metadata": (None, json.dumps(documents_metadata)),
                "files": ("test.pdf", test_pdf, "application/pdf"),
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        mock_job.delay.assert_not_called()

    @patch("argilla_server.api.handlers.v1.documents.upload_document_job")
    async def test_bulk_upload_documents_invalid_metadata(self, mock_job, async_client: AsyncClient):
        """Test bulk upload with invalid metadata."""
        # Create owner user and workspace
        owner = await UserFactory.create(role=UserRole.owner)

        # Create invalid metadata (not JSON)
        documents_metadata = "not valid json"

        # Create a test PDF file
        test_pdf = BytesIO(b"%PDF-1.5 test pdf content")

        # Make request
        response = await async_client.post(
            "/documents/bulk",
            files={
                "documents_metadata": (None, documents_metadata),
                "files": ("test.pdf", test_pdf, "application/pdf"),
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid JSON" in response.json()["detail"]
        mock_job.delay.assert_not_called()

    @patch("argilla_server.api.handlers.v1.documents.upload_document_job")
    async def test_bulk_upload_documents_missing_files(self, mock_job, async_client: AsyncClient):
        """Test bulk upload with missing files."""
        # Create owner user and workspace
        owner = await UserFactory.create(role=UserRole.owner)
        workspace = await WorkspaceFactory.create()

        # Create metadata with reference to non-existent file
        documents_metadata = {
            "documents": [
                {
                    "reference_key": "test_ref",
                    "document_create": {
                        "workspace_id": str(workspace.id),
                        "reference": "test_ref",
                    },
                    "associated_file": "missing.pdf",
                }
            ]
        }

        # Create a test PDF file with different name
        test_pdf = BytesIO(b"%PDF-1.5 test pdf content")

        # Make request
        response = await async_client.post(
            "/documents/bulk",
            files={
                "documents_metadata": (None, json.dumps(documents_metadata)),
                "files": ("test.pdf", test_pdf, "application/pdf"),
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Referenced files not found" in response.json()["detail"]
        mock_job.delay.assert_not_called()

    @patch("argilla_server.api.handlers.v1.documents.upload_document_job")
    async def test_bulk_upload_documents_invalid_workspace(self, mock_job, async_client: AsyncClient):
        """Test bulk upload with invalid workspace ID."""
        # Create owner user
        owner = await UserFactory.create(role=UserRole.owner)

        # Create metadata with non-existent workspace
        documents_metadata = {
            "documents": [
                {
                    "reference_key": "test_ref",
                    "document_create": {
                        "workspace_id": str(uuid4()),  # Non-existent workspace
                        "reference": "test_ref",
                    },
                    "associated_file": "test.pdf",
                }
            ]
        }

        # Create a test PDF file
        test_pdf = BytesIO(b"%PDF-1.5 test pdf content")

        # Make request
        response = await async_client.post(
            "/documents/bulk",
            files={
                "documents_metadata": (None, json.dumps(documents_metadata)),
                "files": ("test.pdf", test_pdf, "application/pdf"),
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "not found" in response.json()["detail"]
        mock_job.delay.assert_not_called()

    @patch("argilla_server.api.handlers.v1.documents.upload_document_job")
    async def test_bulk_upload_documents_success(self, mock_job, async_client: AsyncClient):
        """Test successful bulk upload."""
        # Mock job
        mock_job_instance = MagicMock()
        mock_job_instance.id = "test_job_id"
        mock_job.delay.return_value = mock_job_instance

        # Create owner user and workspace
        owner = await UserFactory.create(role=UserRole.owner)
        workspace = await WorkspaceFactory.create()

        # Create valid metadata
        documents_metadata = {
            "documents": [
                {
                    "reference_key": "test_ref",
                    "document_create": {
                        "workspace_id": str(workspace.id),
                        "reference": "test_ref",
                    },
                    "associated_file": "test.pdf",
                }
            ]
        }

        # Create a test PDF file
        test_pdf = BytesIO(b"%PDF-1.5 test pdf content")

        # Make request
        response = await async_client.post(
            "/documents/bulk",
            files={
                "documents_metadata": (None, json.dumps(documents_metadata)),
                "files": ("test.pdf", test_pdf, "application/pdf"),
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert "job_ids" in response_data
        assert "test_ref" in response_data["job_ids"]
        assert response_data["job_ids"]["test_ref"] == "test_job_id"
        assert response_data["total_documents"] == 1
        assert len(response_data["failed_validations"]) == 0

        # Verify job was created
        mock_job.delay.assert_called_once()

    @patch("argilla_server.api.handlers.v1.documents.upload_document_job")
    async def test_bulk_upload_documents_multiple_files(self, mock_job, async_client: AsyncClient):
        """Test bulk upload with multiple files."""
        # Mock job
        mock_job_instance = MagicMock()
        mock_job_instance.id = "test_job_id"
        mock_job.delay.return_value = mock_job_instance

        # Create owner user and workspace
        owner = await UserFactory.create(role=UserRole.owner)
        workspace = await WorkspaceFactory.create()

        # Create valid metadata with multiple documents
        documents_metadata = {
            "documents": [
                {
                    "reference_key": "ref1",
                    "document_create": {
                        "workspace_id": str(workspace.id),
                        "reference": "ref1",
                    },
                    "associated_file": "test1.pdf",
                },
                {
                    "reference_key": "ref2",
                    "document_create": {
                        "workspace_id": str(workspace.id),
                        "reference": "ref2",
                    },
                    "associated_file": "test2.pdf",
                },
            ]
        }

        # Create test PDF files
        test_pdf1 = BytesIO(b"%PDF-1.5 test pdf content 1")
        test_pdf2 = BytesIO(b"%PDF-1.5 test pdf content 2")

        # Make request
        response = await async_client.post(
            "/documents/bulk",
            files=[
                ("documents_metadata", (None, json.dumps(documents_metadata))),
                ("files", ("test1.pdf", test_pdf1, "application/pdf")),
                ("files", ("test2.pdf", test_pdf2, "application/pdf")),
            ],
        )

        # Verify response
        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert "job_ids" in response_data
        assert "ref1" in response_data["job_ids"]
        assert "ref2" in response_data["job_ids"]
        assert response_data["total_documents"] == 2

        # Verify jobs were created
        assert mock_job.delay.call_count == 2

    @patch("argilla_server.api.handlers.v1.documents.upload_document_job")
    async def test_bulk_upload_documents_partial_failure(self, mock_job, async_client: AsyncClient):
        """Test bulk upload with some files failing validation."""
        # Mock job
        mock_job_instance = MagicMock()
        mock_job_instance.id = "test_job_id"
        mock_job.delay.return_value = mock_job_instance

        # Create owner user and workspace
        owner = await UserFactory.create(role=UserRole.owner)
        workspace = await WorkspaceFactory.create()

        # Create metadata with one valid and one invalid file
        documents_metadata = {
            "documents": [
                {
                    "reference_key": "valid_ref",
                    "document_create": {
                        "workspace_id": str(workspace.id),
                        "reference": "valid_ref",
                    },
                    "associated_file": "valid.pdf",
                },
                {
                    "reference_key": "invalid_ref",
                    "document_create": {
                        "workspace_id": str(workspace.id),
                        "reference": "invalid_ref",
                    },
                    "associated_file": "invalid.txt",  # Not a PDF
                },
            ]
        }

        # Create test files
        valid_pdf = BytesIO(b"%PDF-1.5 valid pdf content")
        invalid_file = BytesIO(b"This is not a PDF file")

        # Make request
        response = await async_client.post(
            "/documents/bulk",
            files=[
                ("documents_metadata", (None, json.dumps(documents_metadata))),
                ("files", ("valid.pdf", valid_pdf, "application/pdf")),
                ("files", ("invalid.txt", invalid_file, "text/plain")),
            ],
        )

        # Verify response
        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert "job_ids" in response_data
        assert "valid_ref" in response_data["job_ids"]
        assert "invalid_ref" not in response_data["job_ids"]
        assert response_data["total_documents"] == 2
        assert len(response_data["failed_validations"]) == 1
        assert "Not a PDF file" in response_data["failed_validations"][0]

        # Verify only one job was created
        mock_job.delay.assert_called_once()
