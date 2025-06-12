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
import uuid
import tempfile
import subprocess

import pytest

from argilla import Argilla, Workspace


@pytest.fixture
def test_workspace_name():
    """Generate a unique test workspace name."""
    return f"test_cli_workspace_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_workspace(client: Argilla, test_workspace_name):
    workspace = Workspace(name=test_workspace_name).create()

    yield workspace

    # Clean up
    try:
        workspace.delete()
    except Exception:
        pass


def run_cli_command(command: str):
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
        result = run_cli_command(f"extralit files list --workspace {test_workspace.name}")

        # Verify the command succeeded
        assert result.returncode == 0
        assert test_workspace.name in result.stdout
        assert "No files found" in result.stdout

    def test_files_upload_and_list_command(self, test_workspace):
        """Test the 'files upload' and 'files list' commands."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content for CLI upload")
            temp_file_path = temp_file.name

        try:
            remote_path = f"test_cli_file_{uuid.uuid4().hex[:8]}.txt"
            upload_result = run_cli_command(
                f"extralit files upload {temp_file_path} --workspace {test_workspace.name} --remote-path {remote_path}"
            )

            assert upload_result.returncode == 0
            assert "File uploaded successfully" in upload_result.stdout

            list_result = run_cli_command(f"extralit files list --workspace {test_workspace.name}")

            assert list_result.returncode == 0
            assert remote_path[:5] in list_result.stdout
        finally:
            os.unlink(temp_file_path)

            try:
                test_workspace.delete_file(remote_path)
            except Exception:
                pass

    def test_files_upload_download_and_delete_command(self, test_workspace):
        """Test the 'files upload', 'files download', and 'files delete' commands."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"Test content for CLI download")
            temp_file_path = temp_file.name

        try:
            remote_path = f"test_cli_download_{uuid.uuid4().hex[:8]}.txt"
            upload_result = run_cli_command(
                f"extralit files upload {temp_file_path} --workspace {test_workspace.name} --remote-path {remote_path}"
            )

            assert upload_result.returncode == 0
            assert "File uploaded successfully" in upload_result.stdout

            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "downloaded_file.txt")

                download_result = run_cli_command(
                    f"extralit files download {remote_path} --workspace {test_workspace.name} --output {output_path}"
                )

                assert download_result.returncode == 0
                assert "File downloaded successfully" in download_result.stdout

                with open(output_path, "rb") as f:
                    content = f.read()
                    assert content == b"Test content for CLI download"

            delete_result = run_cli_command(
                f"extralit files delete {remote_path} --workspace {test_workspace.name} --force"
            )

            assert delete_result.returncode == 0
            assert "File deleted successfully" in delete_result.stdout

            list_result = run_cli_command(f"extralit files list --workspace {test_workspace.name}")

            assert list_result.returncode == 0
            assert remote_path not in list_result.stdout
        finally:
            os.unlink(temp_file_path)

    def test_documents_list_command(self, test_workspace):
        """Test the 'documents list' command."""
        result = run_cli_command(f"extralit documents list --workspace {test_workspace.name}")

        assert result.returncode == 0
        assert "Documents in workspace" in result.stdout or "No documents found" in result.stdout

    def test_documents_add_and_list_command(self, test_workspace):
        """Test the 'documents add' and 'documents list' commands."""
        test_url = f"https://example.com/test_cli_{uuid.uuid4().hex[:8]}"
        add_result = run_cli_command(f"extralit documents add --workspace {test_workspace.name} --url {test_url}")

        assert add_result.returncode == 0
        assert "Document added successfully" in add_result.stdout

        list_result = run_cli_command(f"extralit documents list --workspace {test_workspace.name}")

        # Verify the document is in the list
        assert list_result.returncode == 0
        assert test_url[:10] in list_result.stdout

    def test_schemas_list_command(self, test_workspace, client: Argilla):
        """Test the 'schemas list' command."""
        # Ensure the CLI is logged in for schemas commands
        login_result = run_cli_command(f"extralit login --api-url {client.api_url} --api-key {client.api_key}")
        assert login_result.returncode == 0

        result = run_cli_command(f"extralit schemas list --workspace {test_workspace.name}")

        assert result.returncode == 0, f"\n--- CLI stdout ---\n{result.stdout}\n--- CLI stderr ---\n{result.stderr}\n"
        assert "No schemas found" in result.stdout

    def test_schemas_download_command(self, test_workspace, client: Argilla):
        """Test the 'schemas download' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            login_result = run_cli_command(f"extralit login --api-url {client.api_url} --api-key {client.api_key}")
            assert login_result.returncode == 0

            result = run_cli_command(f"extralit schemas download {temp_dir} --workspace {test_workspace.name}")

            assert (
                result.returncode == 0
            ), f"\n--- CLI stdout ---\n{result.stdout}\n--- CLI stderr ---\n{result.stderr}\n"
            assert "No schemas found" in result.stdout
