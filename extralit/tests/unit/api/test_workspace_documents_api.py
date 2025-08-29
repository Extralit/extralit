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

import os
import tempfile
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from extralit._api._workspaces import WorkspacesAPI
from extralit._models._document import DocumentModel
from extralit.documents import Document


@pytest.fixture
def workspace_api():
    http_client = MagicMock()
    return WorkspacesAPI(http_client=http_client)


@pytest.fixture
def sample_document_id():
    return uuid4()


@pytest.fixture
def sample_workspace_id():
    return uuid4()


@pytest.fixture
def sample_document_model(sample_workspace_id):
    return DocumentModel(
        id=uuid4(),
        workspace_id=sample_workspace_id,
        file_name="test_paper.pdf",
        reference="Smith2023",
        pmid="12345678",
        doi="10.1234/example",
        url="https://example.com/paper.pdf",
        inserted_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_document_data():
    return {
        "id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "file_name": "test_paper.pdf",
        "reference": "Smith2023",
        "pmid": "12345678",
        "doi": "10.1234/example",
        "url": "https://example.com/paper.pdf",
        "inserted_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
    }


class TestDocumentResourceCRUD:
    """Test Document resource CRUD operations."""

    @pytest.fixture
    def mock_client(self):
        """Mock Extralit client with documents API."""
        client = MagicMock()
        documents_api = MagicMock()
        client.api.documents = documents_api
        return client, documents_api

    def test_document_create(self, mock_client, sample_workspace_id):
        """Test Document.create() method."""
        client, documents_api = mock_client

        # Create a document
        doc = Document(workspace_id=sample_workspace_id, reference="Test2023", pmid="87654321", client=client)

        # Mock the API response
        created_model = DocumentModel(
            id=uuid4(), workspace_id=sample_workspace_id, reference="Test2023", pmid="87654321"
        )
        documents_api.create.return_value = created_model

        # Call create
        result = doc.create()

        # Verify API was called
        documents_api.create.assert_called_once()
        created_call_args = documents_api.create.call_args[0][0]
        assert created_call_args.workspace_id == sample_workspace_id
        assert created_call_args.reference == "Test2023"
        assert created_call_args.pmid == "87654321"

        # Verify result
        assert result is doc
        assert doc.id == created_model.id

    def test_document_get(self, mock_client, sample_document_id):
        """Test Document.get() class method."""
        client, documents_api = mock_client
        sample_workspace_id = uuid4()

        # Mock the API response - now returns a list
        retrieved_model = DocumentModel(
            id=sample_document_id,
            workspace_id=sample_workspace_id,
            reference="Retrieved2023",
            file_name="retrieved.pdf",
        )
        documents_api.get.return_value = [retrieved_model]

        # Call get with required workspace_id
        with patch("extralit.documents._resource.Extralit._get_default", return_value=client):
            doc = Document.get(workspace_id=sample_workspace_id, id=sample_document_id)

        # Verify API was called with the new unified method
        documents_api.get.assert_called_once_with(
            {"workspace_id": str(sample_workspace_id), "id": str(sample_document_id)}
        )

        # Verify result
        assert doc.id == sample_document_id
        assert doc.reference == "Retrieved2023"
        assert doc.file_name == "retrieved.pdf"

    def test_document_update(self, mock_client, sample_document_id, sample_workspace_id):
        """Test Document.update() method."""
        client, documents_api = mock_client

        # Create a document with existing data
        doc = Document(workspace_id=sample_workspace_id, reference="Original2023", id=sample_document_id, client=client)

        # Update some fields
        doc.reference = "Updated2023"
        doc.pmid = "11111111"

        # Mock the API response
        updated_model = DocumentModel(
            id=sample_document_id, workspace_id=sample_workspace_id, reference="Updated2023", pmid="11111111"
        )
        documents_api.update.return_value = updated_model

        # Call update
        result = doc.update()

        # Verify API was called
        documents_api.update.assert_called_once()
        updated_call_args = documents_api.update.call_args[0][0]
        assert updated_call_args.id == sample_document_id
        assert updated_call_args.reference == "Updated2023"
        assert updated_call_args.pmid == "11111111"

        # Verify result
        assert result is doc

    def test_document_delete(self, mock_client, sample_document_id, sample_workspace_id):
        """Test Document.delete() method."""
        client, documents_api = mock_client

        # Create a document
        doc = Document(workspace_id=sample_workspace_id, reference="ToDelete2023", id=sample_document_id, client=client)

        # Call delete
        doc.delete()

        # Verify API was called
        documents_api.delete.assert_called_once_with(sample_document_id, sample_workspace_id)

    def test_document_get_by_id_only(self, mock_client, sample_workspace_id):
        """Test Document.get() method now only accepts ID parameter."""
        client, documents_api = mock_client

        # Mock the API response for ID-based get method
        id_model = DocumentModel(
            id=uuid4(),
            workspace_id=sample_workspace_id,
            reference="Test:12345678",
            pmid="12345678",
        )

        with patch("extralit.documents._resource.Extralit._get_default", return_value=client):
            # Test the get method with ID (should work)
            documents_api.get.return_value = [id_model]
            doc = Document.get(workspace_id=sample_workspace_id, id=id_model.id)
            assert doc.id == id_model.id
            assert doc.workspace_id == sample_workspace_id

    def test_document_from_file_local(self, mock_client, sample_workspace_id):
        """Test Document.from_file() with local file."""
        client, documents_api = mock_client

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write("test content")
            tmp_file_path = tmp_file.name

        try:
            with patch("extralit.documents._resource.Extralit._get_default", return_value=client):
                # Test from_file with local path
                doc = Document.from_file(
                    file_path_or_url=tmp_file_path, reference="LocalFile2023", workspace_id=sample_workspace_id
                )

                assert doc.file_path == tmp_file_path
                assert doc.reference == "LocalFile2023"
                assert doc.workspace_id == sample_workspace_id
                assert doc.file_name == os.path.basename(tmp_file_path)
        finally:
            # Clean up
            os.unlink(tmp_file_path)

    def test_document_from_file_url(self, mock_client, sample_workspace_id):
        """Test Document.from_file() with URL."""
        client, documents_api = mock_client

        with patch("extralit.documents._resource.Extralit._get_default", return_value=client):
            # Test from_file with URL
            doc = Document.from_file(
                file_path_or_url="https://example.com/paper.pdf",
                reference="URLFile2023",
                workspace_id=sample_workspace_id,
            )

            assert doc.url == "https://example.com/paper.pdf"
            assert doc.reference == "URLFile2023"
            assert doc.workspace_id == sample_workspace_id
            assert doc.file_name == "paper.pdf"


class TestWorkspaceDocumentIntegration:
    """Test integration between Workspace and Document resources."""

    @pytest.fixture
    def mock_workspace(self, sample_workspace_id):
        """Mock workspace with client."""
        from extralit.workspaces import Workspace

        workspace = MagicMock(spec=Workspace)
        workspace.id = sample_workspace_id
        workspace._client = MagicMock()
        workspace._client.api.documents = MagicMock()
        return workspace

    def test_workspace_documents_property(self, mock_workspace, sample_document_model):
        """Test workspace.documents property returns Documents collection."""
        from extralit.client.resources import Documents

        # Mock the Documents collection and its behavior
        mock_documents_collection = MagicMock(spec=Documents)
        mock_documents_collection.list.return_value = [
            Document.from_model(model=sample_document_model, client=mock_workspace._client)
        ]

        # Mock the documents property to return our Documents collection
        mock_workspace.documents = mock_documents_collection

        documents_collection = mock_workspace.documents
        documents_list = documents_collection.list()

        assert len(documents_list) == 1
        assert isinstance(documents_list[0], Document)
        assert documents_list[0].id == sample_document_model.id

    def test_workspace_add_document_integration(self, mock_workspace, sample_workspace_id):
        """Test workspace.add_document creates Document and calls API."""
        # Mock the actual add_document method behavior
        mock_workspace.add_document.return_value = uuid4()

        # Call add_document
        doc_id = mock_workspace.add_document(file_path="/path/to/paper.pdf", reference="Integration2023")

        # Verify it was called
        mock_workspace.add_document.assert_called_once()
        assert isinstance(doc_id, UUID)
