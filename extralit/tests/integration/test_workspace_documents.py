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
import uuid

from extralit import Workspace
from extralit.client.resources import Documents


class TestWorkspaceDocuments:
    def test_list_documents(self, workspace: Workspace):
        """Test listing documents in a workspace using the new Documents resource."""
        # Get the documents collection
        documents_collection = workspace.documents

        # Verify it's a Documents instance
        assert isinstance(documents_collection, Documents)

        # Test listing documents (should return a list)
        documents_list = documents_collection.list()
        assert isinstance(documents_list, list)
        # Initially, there should be no documents
        assert len(documents_list) == 0

        # Test len() method on collection
        assert len(documents_collection) == 0

    def test_documents_collection_iteration(self, workspace: Workspace):
        """Test that the Documents collection can be iterated over."""
        documents_collection = workspace.documents

        # Should be able to iterate (even if empty)
        document_list = list(documents_collection)
        assert isinstance(document_list, list)
        assert len(document_list) == 0

    def test_add_and_list_documents(self, workspace: Workspace):
        """Test adding a document to a workspace and listing it."""
        # Add a document with a URL
        test_url = f"https://example.com/test_{uuid.uuid4()}"
        document_id = workspace.add_document(url=test_url, reference="test-ref-url")

        # Verify the document ID
        assert document_id is not None

        # Get documents collection and list documents
        documents_collection = workspace.documents
        documents_list = documents_collection.list()

        # Verify the document is in the list
        assert len(documents_collection) > 0
        assert len(documents_list) > 0
        assert any(doc.url == test_url for doc in documents_list)

    def test_add_document_with_pmid(self, workspace: Workspace):
        """Test adding a document with a PMID."""
        # Add a document with a PMID
        test_pmid = f"PMC{uuid.uuid4().hex[:8]}"
        document_id = workspace.add_document(
            url=f"https://example.com/{test_pmid}.pdf", pmid=test_pmid, reference="test-ref-pmid"
        )

        # Verify the document ID
        assert document_id is not None

        # Get documents collection and list documents
        documents_collection = workspace.documents
        documents_list = documents_collection.list()

        # Verify the document is in the list
        assert len(documents_collection) > 0
        assert len(documents_list) > 0
        assert any(doc.pmid == test_pmid for doc in documents_list)

    def test_add_document_with_doi(self, workspace: Workspace):
        """Test adding a document with a DOI."""
        # Add a document with a DOI
        test_doi = f"10.1234/{uuid.uuid4().hex[:8]}"
        document_id = workspace.add_document(
            url=f"https://example.com/{test_doi}.pdf", doi=test_doi, reference="test-ref-doi"
        )

        # Verify the document ID
        assert document_id is not None

        # Get documents collection and list documents
        documents_collection = workspace.documents
        documents_list = documents_collection.list()

        # Verify the document is in the list
        assert len(documents_collection) > 0
        assert len(documents_list) > 0
        assert any(doc.doi == test_doi for doc in documents_list)

    def test_add_document_with_file(self, workspace: Workspace):
        """Test adding a document with a file."""
        # Create a temporary PDF-like file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(b"%PDF-1.4\nTest PDF content")
            temp_file_path = temp_file.name

        try:
            # Add a document with a file
            document_id = workspace.add_document(file_path=temp_file_path, reference="test-ref-file")

            # Verify the document ID
            assert document_id is not None

            # Get documents collection and list documents
            documents_collection = workspace.documents
            documents_list = documents_collection.list()

            # Verify the document is in the list
            assert len(documents_collection) > 0
            assert len(documents_list) > 0

            # Note: Since the file is uploaded, we can't verify its content directly
            # But we can verify that a document was added
            assert len(documents_list) > 0
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)

    def test_documents_get_by_id(self, workspace: Workspace):
        """Test getting a document by ID using the Documents collection."""
        # Add a document first
        test_url = f"https://example.com/test_{uuid.uuid4()}"
        document_id = workspace.add_document(url=test_url, reference="test-ref-get-by-id")
        assert document_id is not None

        # Get the document by ID using the Documents collection
        documents_collection = workspace.documents
        document = documents_collection(id=document_id)

        # Verify we got the document
        assert document is not None
        assert document.id == document_id
        assert document.url == test_url

    def test_documents_get_by_pmid(self, workspace: Workspace):
        """Test getting a document by PMID using the Documents collection."""
        # Add a document with a PMID
        test_pmid = f"PMC{uuid.uuid4().hex[:8]}"
        document_id = workspace.add_document(
            url=f"https://example.com/{test_pmid}.pdf", pmid=test_pmid, reference="test-ref-get-by-pmid"
        )
        assert document_id is not None

        # Get the document by PMID using the Documents collection
        documents_collection = workspace.documents
        document = documents_collection(pmid=test_pmid)

        # Verify we got the document
        assert document is not None
        assert document.pmid == test_pmid

    def test_documents_get_by_doi(self, workspace: Workspace):
        """Test getting a document by DOI using the Documents collection."""
        # Add a document with a DOI
        test_doi = f"10.1234/{uuid.uuid4().hex[:8]}"
        document_id = workspace.add_document(
            url=f"https://example.com/{test_doi}.pdf", doi=test_doi, reference="test-ref-get-by-doi"
        )
        assert document_id is not None

        # Get the document by DOI using the Documents collection
        documents_collection = workspace.documents
        document = documents_collection(doi=test_doi)

        # Verify we got the document
        assert document is not None
        assert document.doi == test_doi

    def test_documents_get_by_reference(self, workspace: Workspace):
        """Test getting a document by reference using the Documents collection."""
        # Add a document with a unique reference
        test_reference = f"test-ref-unique-{uuid.uuid4().hex[:8]}"
        test_url = f"https://example.com/test_{uuid.uuid4()}"
        document_id = workspace.add_document(url=test_url, reference=test_reference)
        assert document_id is not None

        # Get the document by reference using the Documents collection
        documents_collection = workspace.documents
        document = documents_collection(reference=test_reference)

        # Verify we got the document
        assert document is not None
        assert document.reference == test_reference

    def test_documents_get_nonexistent(self, workspace: Workspace):
        """Test getting a nonexistent document returns None."""
        documents_collection = workspace.documents

        # Try to get a document that doesn't exist
        document = documents_collection(id=uuid.uuid4())
        assert document is None

    def test_documents_get_no_params_error(self, workspace: Workspace):
        """Test that calling Documents() without parameters raises an error."""
        from extralit._exceptions import ExtralitError

        documents_collection = workspace.documents

        # Should raise an error when no parameters are provided
        try:
            # Use type: ignore to suppress the linter error since we're intentionally testing invalid usage
            documents_collection()  # type: ignore
            raise AssertionError("Expected an error when calling with no parameters")
        except ExtralitError as e:
            assert "must be provided" in str(e)
