# Copyright 2024-present, Argilla, Inc.
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
import uuid
import tempfile
from pathlib import Path

import pytest

from argilla import Argilla, Workspace


class TestWorkspaceDocuments:
    def test_list_documents(self, workspace: Workspace):
        """Test listing documents in a workspace."""
        # List documents in the workspace
        documents = workspace.get_documents()
        
        # Verify the result
        assert isinstance(documents, list)
        # Initially, there should be no documents
        assert len(documents) == 0
    
    def test_add_and_list_documents(self, workspace: Workspace):
        """Test adding a document to a workspace and listing it."""
        # Add a document with a URL
        test_url = f"https://example.com/test_{uuid.uuid4()}"
        document_id = workspace.add_document(url=test_url)
        
        # Verify the document ID
        assert document_id is not None
        
        # List documents in the workspace
        documents = workspace.get_documents()
        
        # Verify the document is in the list
        assert len(documents) > 0
        assert any(doc.url == test_url for doc in documents)
    
    def test_add_document_with_pmid(self, workspace: Workspace):
        """Test adding a document with a PMID."""
        # Add a document with a PMID
        test_pmid = f"PMC{uuid.uuid4().hex[:8]}"
        document_id = workspace.add_document(pmid=test_pmid)
        
        # Verify the document ID
        assert document_id is not None
        
        # List documents in the workspace
        documents = workspace.get_documents()
        
        # Verify the document is in the list
        assert len(documents) > 0
        assert any(doc.pmid == test_pmid for doc in documents)
    
    def test_add_document_with_doi(self, workspace: Workspace):
        """Test adding a document with a DOI."""
        # Add a document with a DOI
        test_doi = f"10.1234/{uuid.uuid4().hex[:8]}"
        document_id = workspace.add_document(doi=test_doi)
        
        # Verify the document ID
        assert document_id is not None
        
        # List documents in the workspace
        documents = workspace.get_documents()
        
        # Verify the document is in the list
        assert len(documents) > 0
        assert any(doc.doi == test_doi for doc in documents)
    
    def test_add_document_with_file(self, workspace: Workspace):
        """Test adding a document with a file."""
        # Create a temporary PDF-like file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(b"%PDF-1.4\nTest PDF content")
            temp_file_path = temp_file.name
        
        try:
            # Add a document with a file
            document_id = workspace.add_document(file_path=temp_file_path)
            
            # Verify the document ID
            assert document_id is not None
            
            # List documents in the workspace
            documents = workspace.get_documents()
            
            # Verify the document is in the list
            assert len(documents) > 0
            
            # Note: Since the file is uploaded, we can't verify its content directly
            # But we can verify that a document was added
            assert len(documents) > 0
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
