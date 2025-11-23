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
import subprocess
import tempfile
import uuid

import pytest
from unittest.mock import patch
from extralit import Extralit, Workspace
from pathlib import Path

@pytest.fixture
def test_workspace_name():
    """Generate a unique test workspace name."""
    return f"test-workspace{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_workspace(client: Extralit, test_workspace_name):
    with patch("extralit._api._workspaces.WorkspacesAPI.create") as mock_create:
        mock_create.return_value = {
            "id": str(uuid.uuid4()),
            "name": test_workspace_name,
        }

        # Create "fake" workspace object (not hitting real API)
        ws = Workspace(name=test_workspace_name)
        ws.id = mock_create.return_value["id"]

        yield ws


from pathlib import Path
import tempfile
import subprocess
import os

def run_cli_command(command: str):
    """Run CLI in fully isolated subprocess with Path.home patched BEFORE imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_home = Path(tmpdir) / "home"
        fake_home.mkdir()

        config_dir = fake_home / ".config" / "extralit"
        config_dir.mkdir(parents=True)
        (config_dir / "session.json").write_text("""{
            "api_url": "http://localhost:9999",
            "api_key": "fake",
            "user": {"username": "test-user", "email": "test@example.com"}
        }""")

        fake_home_str = str(fake_home)

        script = f"""
import os
from pathlib import Path
from unittest.mock import patch

# Patch Path.home BEFORE any extralit import
with patch('pathlib.Path.home', return_value=Path({fake_home_str!r})):
    os.environ['HOME'] = {fake_home_str!r}
    os.environ['USERPROFILE'] = {fake_home_str!r}

    # NOW import and patch everything else
    from extralit import Extralit
    import subprocess
    import shlex

    with patch('extralit._api._client.APIClient._validate_connection'):
        client = Extralit(api_url="http://localhost:9999", api_key="fake")

        with patch('extralit.cli.callback.init_callback', return_value=client):
            with patch('extralit.cli.workspaces.__main__.init_callback', return_value=client):
                result = subprocess.run(shlex.split('{command}'), capture_output=True, text=True)
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                exit(result.returncode)
"""

        script_path = fake_home / "run.py"
        script_path.write_text(script)

        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(fake_home)
        )

        return subprocess.CompletedProcess(
            args=command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )
    
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

    @pytest.mark.skip(reason="buckets with versioning enabled still list deleted files, needs further investigation")
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
        add_result = run_cli_command(
            f"extralit documents add --workspace {test_workspace.name} --reference test_url --url {test_url}"
        )

        assert add_result.returncode == 0
        assert "Document added successfully" in add_result.stdout

        list_result = run_cli_command(f"extralit documents list --workspace {test_workspace.name}")

        # Verify the document is in the list
        assert list_result.returncode == 0
        assert test_url[:10] in list_result.stdout

    def test_schemas_list_command(self, test_workspace, client: Extralit):
        """Test the 'schemas list' command."""
        # Ensure the CLI is logged in for schemas commands
        login_result = run_cli_command(f"extralit login --api-url {client.api_url} --api-key {client.api_key}")
        assert login_result.returncode == 0

        result = run_cli_command(f"extralit schemas list --workspace {test_workspace.name}")

        assert result.returncode == 0, f"\n--- CLI stdout ---\n{result.stdout}\n--- CLI stderr ---\n{result.stderr}\n"
        assert "No schemas found" in result.stdout

    def test_schemas_download_command(self, test_workspace, client: Extralit):
        """Test the 'schemas download' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            login_result = run_cli_command(f"extralit login --api-url {client.api_url} --api-key {client.api_key}")
            assert login_result.returncode == 0

            result = run_cli_command(f"extralit schemas download {temp_dir} --workspace {test_workspace.name}")

            assert result.returncode == 0, (
                f"\n--- CLI stdout ---\n{result.stdout}\n--- CLI stderr ---\n{result.stderr}\n"
            )
            assert "No schemas found" in result.stdout

    from unittest.mock import patch

    def test_workspace_doctor_command(self, test_workspace, httpx_mock, client: Extralit):
        """Test the 'workspaces doctor' command with autofix enabled."""
        from typer.testing import CliRunner
        from extralit.cli.workspaces.__main__ import app
        from unittest.mock import patch
        
        runner = CliRunner()
        
        # Mock the user's workspaces list endpoint
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:9999/api/v1/me/workspaces",
            json={"items": [{
                "id": str(test_workspace.id), 
                "name": test_workspace.name,
                "inserted_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }]}
        )
        
        # Mock the doctor endpoint
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:9999/api/v1/workspaces/{test_workspace.id}/doctor?autofix=true",
            json={
                "workspace_id": str(test_workspace.id),
                "workspace_name": test_workspace.name,
                "overall_status": "healthy",
                "checks": []
            }
        )
        
        # Patch init_callback to return our test client
        with patch('extralit.cli.workspaces.__main__.init_callback', return_value=client):
            result = runner.invoke(app, ["--name", test_workspace.name, "doctor"])
        
        assert result.exit_code == 0, f"CLI failed:\n{result.stdout}\n{result.exception if result.exception else ''}"
        assert "healthy" in result.stdout.lower()


    def test_workspace_doctor_command_no_autofix(self, test_workspace, httpx_mock, client: Extralit):
        """Test the 'workspaces doctor' command with autofix disabled."""
        from typer.testing import CliRunner
        from extralit.cli.workspaces.__main__ import app
        from unittest.mock import patch
        
        runner = CliRunner()
        
        # Mock the user's workspaces list endpoint
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:9999/api/v1/me/workspaces",
            json={"items": [{
                "id": str(test_workspace.id), 
                "name": test_workspace.name,
                "inserted_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }]}
        )
        
        # Mock the doctor endpoint
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:9999/api/v1/workspaces/{test_workspace.id}/doctor?autofix=false",
            json={
                "workspace_id": str(test_workspace.id),
                "workspace_name": test_workspace.name,
                "overall_status": "healthy",
                "checks": []
            }
        )
        
        # Patch init_callback to return our test client
        with patch('extralit.cli.workspaces.__main__.init_callback', return_value=client):
            result = runner.invoke(app, ["--name", test_workspace.name, "doctor", "--no-autofix"])
        
        assert result.exit_code == 0, f"CLI failed:\n{result.stdout}\n{result.exception if result.exception else ''}"
        assert "healthy" in result.stdout.lower()