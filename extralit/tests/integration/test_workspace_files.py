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


class TestWorkspaceFiles:
    def test_list_files(self, workspace: Workspace):
        """Test listing files in a workspace."""
        # List files in the workspace
        files = workspace.list_files("")
        
        # Verify the result
        assert hasattr(files, "objects")
        # Initially, there should be no files
        assert len(files.objects) == 0
    
    def test_upload_and_list_files(self, workspace: Workspace):
        """Test uploading a file to a workspace and listing it."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content")
            temp_file_path = temp_file.name
        
        try:
            # Upload the file
            remote_path = f"test_file_{uuid.uuid4()}.txt"
            file_metadata = workspace.put_file(remote_path, temp_file_path)
            
            # Verify the file metadata
            assert file_metadata.object_name == remote_path
            
            # List files in the workspace
            files = workspace.list_files("")
            
            # Verify the file is in the list
            assert len(files.objects) > 0
            assert any(file.object_name == remote_path for file in files.objects)
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            # Clean up the remote file
            try:
                workspace.delete_file(remote_path)
            except Exception:
                pass
    
    def test_upload_download_and_delete_file(self, workspace: Workspace):
        """Test uploading, downloading, and deleting a file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content for download")
            temp_file_path = temp_file.name
        
        try:
            # Upload the file
            remote_path = f"test_download_{uuid.uuid4()}.txt"
            file_metadata = workspace.put_file(remote_path, temp_file_path)
            
            # Verify the file metadata
            assert file_metadata.object_name == remote_path
            
            # Download the file
            file_response = workspace.get_file(remote_path)
            
            # Verify the file content
            assert file_response.content == b"Test content for download"
            
            # Delete the file
            workspace.delete_file(remote_path)
            
            # Verify the file is deleted
            files = workspace.list_files("")
            assert not any(file.object_name == remote_path for file in files.objects)
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    def test_file_operations_with_subdirectories(self, workspace: Workspace):
        """Test file operations with subdirectories."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content in subdirectory")
            temp_file_path = temp_file.name
        
        try:
            # Upload the file to a subdirectory
            subdir = f"test_subdir_{uuid.uuid4()}"
            remote_path = f"{subdir}/test_file.txt"
            file_metadata = workspace.put_file(remote_path, temp_file_path)
            
            # Verify the file metadata
            assert file_metadata.object_name == remote_path
            
            # List files in the subdirectory
            files = workspace.list_files(subdir)
            
            # Verify the file is in the list
            assert len(files.objects) > 0
            assert any(file.object_name == remote_path for file in files.objects)
            
            # Download the file
            file_response = workspace.get_file(remote_path)
            
            # Verify the file content
            assert file_response.content == b"Test content in subdirectory"
            
            # Delete the file
            workspace.delete_file(remote_path)
            
            # Verify the file is deleted
            files = workspace.list_files(subdir)
            assert not any(file.object_name == remote_path for file in files.objects)
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
