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
import subprocess
from pathlib import Path

import pytest

from argilla import Argilla, Workspace


@pytest.fixture
def test_workspace_name():
    """Generate a unique test workspace name."""
    return f"test_cli_workspace_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_workspace(client: Argilla, test_workspace_name):
    """Create a test workspace for CLI commands."""
    # Create the workspace
    workspace = Workspace(name=test_workspace_name).create()
    
    yield workspace
    
    # Clean up
    try:
        workspace.delete()
    except Exception:
        pass


def run_cli_command(command):
    """Run a CLI command and return the result."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
    )
    return result


class TestCLICommands:
    def test_files_list_command(self, test_workspace):
        """Test the 'files list' command."""
        # Run the command
        result = run_cli_command(f"python -m argilla.cli files list --workspace {test_workspace.name}")
        
        # Verify the command succeeded
        assert result.returncode == 0
        assert "Files in workspace" in result.stdout
        assert "No files found" in result.stdout
    
    def test_files_upload_and_list_command(self, test_workspace):
        """Test the 'files upload' and 'files list' commands."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content for CLI upload")
            temp_file_path = temp_file.name
        
        try:
            # Upload the file
            remote_path = f"test_cli_file_{uuid.uuid4().hex[:8]}.txt"
            upload_result = run_cli_command(
                f"python -m argilla.cli files upload {temp_file_path} --workspace {test_workspace.name} --remote-path {remote_path}"
            )
            
            # Verify the upload succeeded
            assert upload_result.returncode == 0
            assert "File uploaded successfully" in upload_result.stdout
            
            # List the files
            list_result = run_cli_command(f"python -m argilla.cli files list --workspace {test_workspace.name}")
            
            # Verify the file is in the list
            assert list_result.returncode == 0
            assert remote_path in list_result.stdout
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            # Clean up the remote file
            try:
                test_workspace.delete_file(remote_path)
            except Exception:
                pass
    
    def test_files_upload_download_and_delete_command(self, test_workspace):
        """Test the 'files upload', 'files download', and 'files delete' commands."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content for CLI download")
            temp_file_path = temp_file.name
        
        try:
            # Upload the file
            remote_path = f"test_cli_download_{uuid.uuid4().hex[:8]}.txt"
            upload_result = run_cli_command(
                f"python -m argilla.cli files upload {temp_file_path} --workspace {test_workspace.name} --remote-path {remote_path}"
            )
            
            # Verify the upload succeeded
            assert upload_result.returncode == 0
            assert "File uploaded successfully" in upload_result.stdout
            
            # Create a temporary directory for download
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "downloaded_file.txt")
                
                # Download the file
                download_result = run_cli_command(
                    f"python -m argilla.cli files download {remote_path} --workspace {test_workspace.name} --output {output_path}"
                )
                
                # Verify the download succeeded
                assert download_result.returncode == 0
                assert "File downloaded successfully" in download_result.stdout
                
                # Verify the file content
                with open(output_path, "rb") as f:
                    content = f.read()
                    assert content == b"Test content for CLI download"
            
            # Delete the file
            delete_result = run_cli_command(
                f"python -m argilla.cli files delete {remote_path} --workspace {test_workspace.name} --force"
            )
            
            # Verify the delete succeeded
            assert delete_result.returncode == 0
            assert "File deleted successfully" in delete_result.stdout
            
            # List the files to verify deletion
            list_result = run_cli_command(f"python -m argilla.cli files list --workspace {test_workspace.name}")
            
            # Verify the file is not in the list
            assert list_result.returncode == 0
            assert remote_path not in list_result.stdout
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    def test_documents_list_command(self, test_workspace):
        """Test the 'documents list' command."""
        # Run the command
        result = run_cli_command(f"python -m argilla.cli documents list --workspace {test_workspace.name}")
        
        # Verify the command succeeded
        assert result.returncode == 0
        assert "Documents in workspace" in result.stdout or "No documents found" in result.stdout
    
    def test_documents_add_and_list_command(self, test_workspace):
        """Test the 'documents add' and 'documents list' commands."""
        # Add a document
        test_url = f"https://example.com/test_cli_{uuid.uuid4().hex[:8]}"
        add_result = run_cli_command(
            f"python -m argilla.cli documents add --workspace {test_workspace.name} --url {test_url}"
        )
        
        # Verify the add succeeded
        assert add_result.returncode == 0
        assert "Document added successfully" in add_result.stdout
        
        # List the documents
        list_result = run_cli_command(f"python -m argilla.cli documents list --workspace {test_workspace.name}")
        
        # Verify the document is in the list
        assert list_result.returncode == 0
        assert test_url in list_result.stdout
    
    def test_schemas_download_command(self, test_workspace):
        """Test the 'schemas download' command."""
        # Create a temporary directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run the command
            result = run_cli_command(
                f"python -m argilla.cli schemas download {temp_dir} --workspace {test_workspace.name}"
            )
            
            # Verify the command succeeded
            assert result.returncode == 0
            # Since there are no schemas, it should say "No schemas found"
            assert "No schemas found" in result.stdout
