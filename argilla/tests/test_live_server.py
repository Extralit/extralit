#!/usr/bin/env python
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

"""
Test script for testing Argilla CLI and API with a live server.

This script tests the following functionality:
1. Login and authentication
2. Workspace management
3. File operations
4. Document operations
5. Schema operations

Usage:
    python test_live_server.py --api-url <api_url> --api-key <api_key>
"""

import os
import sys
import uuid
import argparse
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

try:
    import pandera as pa
    from extralit.extraction.models import SchemaStructure
    PANDERA_AVAILABLE = True
except ImportError:
    PANDERA_AVAILABLE = False
    print("Warning: pandera and extralit are not available. Schema tests will be skipped.")

import argilla as rg
from argilla import Argilla, Workspace


def run_command(command, expected_success=True):
    """Run a command and print the result."""
    print(f"\nRunning command: {command}")
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
    )
    
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    
    if expected_success:
        assert result.returncode == 0, f"Command failed with return code {result.returncode}"
    else:
        assert result.returncode != 0, f"Command succeeded but was expected to fail"
    
    return result


def test_login(api_url, api_key):
    """Test login and authentication."""
    print("\n=== Testing Login and Authentication ===")
    
    # Test login with API key
    run_command(f"python -m argilla.cli login --api-url {api_url} --api-key {api_key}")
    
    # Test whoami
    run_command("python -m argilla.cli whoami")
    
    # Test info
    run_command("python -m argilla.cli info")
    
    print("Login and authentication tests passed!")


def test_workspace_management(client):
    """Test workspace management."""
    print("\n=== Testing Workspace Management ===")
    
    # Generate a unique workspace name
    workspace_name = f"test_workspace_{uuid.uuid4().hex[:8]}"
    
    # Test creating a workspace
    run_command(f"python -m argilla.cli workspaces create --name {workspace_name}")
    
    # Test listing workspaces
    list_result = run_command("python -m argilla.cli workspaces list")
    assert workspace_name in list_result.stdout, f"Workspace {workspace_name} not found in list"
    
    # Get the workspace from the client
    workspace = client.workspaces(name=workspace_name)
    assert workspace is not None, f"Workspace {workspace_name} not found in client"
    
    # Clean up
    run_command(f"python -m argilla.cli workspaces delete --name {workspace_name} --force")
    
    print("Workspace management tests passed!")
    return workspace_name


def test_file_operations(client, workspace_name):
    """Test file operations."""
    print("\n=== Testing File Operations ===")
    
    # Create a workspace
    workspace = Workspace(name=workspace_name).create()
    
    try:
        # Test listing files (should be empty)
        run_command(f"python -m argilla.cli files list --workspace {workspace_name}")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content for live server test")
            temp_file_path = temp_file.name
        
        try:
            # Test uploading a file
            remote_path = f"test_file_{uuid.uuid4().hex[:8]}.txt"
            run_command(f"python -m argilla.cli files upload {temp_file_path} --workspace {workspace_name} --remote-path {remote_path}")
            
            # Test listing files (should contain the uploaded file)
            list_result = run_command(f"python -m argilla.cli files list --workspace {workspace_name}")
            assert remote_path in list_result.stdout, f"File {remote_path} not found in list"
            
            # Test downloading the file
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "downloaded_file.txt")
                run_command(f"python -m argilla.cli files download {remote_path} --workspace {workspace_name} --output {output_path}")
                
                # Verify the file content
                with open(output_path, "rb") as f:
                    content = f.read()
                    assert content == b"Test content for live server test", "Downloaded file content does not match"
            
            # Test deleting the file
            run_command(f"python -m argilla.cli files delete {remote_path} --workspace {workspace_name} --force")
            
            # Test listing files (should be empty again)
            list_result = run_command(f"python -m argilla.cli files list --workspace {workspace_name}")
            assert remote_path not in list_result.stdout, f"File {remote_path} still in list after deletion"
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    finally:
        # Clean up the workspace
        workspace.delete()
    
    print("File operations tests passed!")


def test_document_operations(client, workspace_name):
    """Test document operations."""
    print("\n=== Testing Document Operations ===")
    
    # Create a workspace
    workspace = Workspace(name=workspace_name).create()
    
    try:
        # Test listing documents (should be empty)
        run_command(f"python -m argilla.cli documents list --workspace {workspace_name}")
        
        # Test adding a document with a URL
        test_url = f"https://example.com/test_{uuid.uuid4().hex[:8]}"
        run_command(f"python -m argilla.cli documents add --workspace {workspace_name} --url {test_url}")
        
        # Test listing documents (should contain the added document)
        list_result = run_command(f"python -m argilla.cli documents list --workspace {workspace_name}")
        assert test_url in list_result.stdout, f"Document with URL {test_url} not found in list"
        
        # Test adding a document with a PMID
        test_pmid = f"PMC{uuid.uuid4().hex[:8]}"
        run_command(f"python -m argilla.cli documents add --workspace {workspace_name} --pmid {test_pmid}")
        
        # Test listing documents (should contain both documents)
        list_result = run_command(f"python -m argilla.cli documents list --workspace {workspace_name}")
        assert test_pmid in list_result.stdout, f"Document with PMID {test_pmid} not found in list"
        
        # Test adding a document with a DOI
        test_doi = f"10.1234/{uuid.uuid4().hex[:8]}"
        run_command(f"python -m argilla.cli documents add --workspace {workspace_name} --doi {test_doi}")
        
        # Test listing documents (should contain all three documents)
        list_result = run_command(f"python -m argilla.cli documents list --workspace {workspace_name}")
        assert test_doi in list_result.stdout, f"Document with DOI {test_doi} not found in list"
        
        # Note: Document deletion is not yet implemented in the API
    finally:
        # Clean up the workspace
        workspace.delete()
    
    print("Document operations tests passed!")


def test_schema_operations(client, workspace_name):
    """Test schema operations."""
    print("\n=== Testing Schema Operations ===")
    
    if not PANDERA_AVAILABLE:
        print("Skipping schema tests because pandera and extralit are not available")
        return
    
    # Create a workspace
    workspace = Workspace(name=workspace_name).create()
    
    try:
        # Create a test schema
        schema = pa.DataFrameSchema(
            name=f"test_schema_{uuid.uuid4().hex[:8]}",
            columns={
                "text": pa.Column(pa.String),
                "label": pa.Column(pa.String),
                "score": pa.Column(pa.Float, nullable=True),
            },
        )
        
        # Create a temporary file with the schema
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            temp_file.write(schema.to_json().encode())
            temp_file_path = temp_file.name
        
        try:
            # Create a temporary directory for schema files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy the schema file to the directory
                schema_file_path = os.path.join(temp_dir, f"{schema.name}.json")
                with open(schema_file_path, "w") as f:
                    f.write(schema.to_json())
                
                # Test uploading the schema
                run_command(f"python -m argilla.cli schemas upload {temp_dir} --workspace {workspace_name}")
                
                # Test listing schemas
                list_result = run_command(f"python -m argilla.cli schemas list --workspace {workspace_name}")
                assert schema.name in list_result.stdout, f"Schema {schema.name} not found in list"
                
                # Create a temporary directory for downloading schemas
                with tempfile.TemporaryDirectory() as download_dir:
                    # Test downloading schemas
                    run_command(f"python -m argilla.cli schemas download {download_dir} --workspace {workspace_name}")
                    
                    # Verify the schema file exists
                    downloaded_file = os.path.join(download_dir, f"{schema.name}.json")
                    assert os.path.exists(downloaded_file), f"Downloaded schema file {downloaded_file} does not exist"
                    
                    # Verify the schema content
                    with open(downloaded_file, "r") as f:
                        content = f.read()
                        loaded_schema = pa.DataFrameSchema.from_json(content)
                        assert loaded_schema.name == schema.name, "Schema name does not match"
                        assert "text" in loaded_schema.columns, "Schema missing 'text' column"
                        assert "label" in loaded_schema.columns, "Schema missing 'label' column"
                        assert "score" in loaded_schema.columns, "Schema missing 'score' column"
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    finally:
        # Clean up the workspace
        workspace.delete()
    
    print("Schema operations tests passed!")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Argilla CLI and API with a live server")
    parser.add_argument("--api-url", required=True, help="Argilla API URL")
    parser.add_argument("--api-key", required=True, help="Argilla API key")
    args = parser.parse_args()
    
    # Initialize the client
    client = Argilla(api_url=args.api_url, api_key=args.api_key)
    
    print(f"Testing with Argilla server at {args.api_url}")
    print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test login and authentication
        test_login(args.api_url, args.api_key)
        
        # Test workspace management
        workspace_name = test_workspace_management(client)
        
        # Test file operations
        test_file_operations(client, workspace_name)
        
        # Test document operations
        test_document_operations(client, workspace_name)
        
        # Test schema operations
        test_schema_operations(client, workspace_name)
        
        print("\n=== All tests passed! ===")
        print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return 0
    except Exception as e:
        print(f"\n=== Tests failed: {str(e)} ===")
        print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
