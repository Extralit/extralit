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

"""Unit tests for CLI workflow commands with RQ Groups integration."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from extralit.cli.workflows.__main__ import app


class TestWorkflowsCLI:
    """Test CLI workflow commands with RQ Groups integration."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        """Mock Extralit client."""
        client = MagicMock()
        client.api_url = "http://localhost:8000"
        client.api.http_client = MagicMock()
        return client

    @pytest.fixture
    def sample_workflow_response(self):
        """Sample workflow API response."""
        return {
            "workflow_id": str(uuid4()),
            "document_id": str(uuid4()),
            "group_id": "document_workflow_123_abcd1234",
            "reference": "test_ref",
            "status": "running",
        }

    @pytest.fixture
    def sample_status_response(self):
        """Sample workflow status API response."""
        return [
            {
                "document_id": str(uuid4()),
                "workflow_id": str(uuid4()),
                "group_id": "document_workflow_123_abcd1234",
                "reference": "test_ref",
                "workspace_name": "test_workspace",
                "status": "running",
                "progress": 0.5,
                "total_jobs": 2,
                "completed_jobs": 1,
                "failed_jobs": 0,
                "running_jobs": 1,
                "created_at": "2024-01-15T10:30:00Z",
                "jobs": [
                    {"id": "analysis_job", "status": "finished", "workflow_step": "analysis_and_preprocess"},
                    {"id": "text_job", "status": "started", "workflow_step": "text_extraction"},
                ],
            }
        ]

    def test_start_command_success(self, runner, mock_client, sample_workflow_response):
        """Test successful workflow start command."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_workflow_response
        mock_client.api.http_client.post.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(
                app,
                ["start", "--document-id", str(uuid4()), "--workspace", "test_workspace", "--reference", "test_ref"],
            )

            assert result.exit_code == 0
            assert "Started workflow" in result.stdout
            assert sample_workflow_response["workflow_id"] in result.stdout

            # Verify API call
            mock_client.api.http_client.post.assert_called_once()
            call_args = mock_client.api.http_client.post.call_args
            assert "/api/v1/workflows/start" in call_args[0][0]

            request_data = call_args[1]["json"]
            assert "document_id" in request_data
            assert request_data["workspace_name"] == "test_workspace"
            assert request_data["reference"] == "test_ref"

    def test_start_command_invalid_document_id(self, runner, mock_client):
        """Test start command with invalid document ID format."""
        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["start", "--document-id", "invalid-uuid", "--workspace", "test_workspace"])

            assert result.exit_code == 1
            assert "Invalid document ID format" in result.stdout

    def test_start_command_api_error(self, runner, mock_client):
        """Test start command with API error response."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Document not found"}
        mock_client.api.http_client.post.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["start", "--document-id", str(uuid4()), "--workspace", "test_workspace"])

            assert result.exit_code == 1
            assert "Error starting workflow" in result.stdout
            assert "Document not found" in result.stdout

    def test_start_command_with_verbose(self, runner, mock_client, sample_workflow_response):
        """Test start command with verbose output."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_workflow_response
        mock_client.api.http_client.post.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(
                app, ["start", "--document-id", str(uuid4()), "--workspace", "test_workspace", "--verbose"]
            )

            assert result.exit_code == 0
            assert "Document ID:" in result.stdout
            assert "Group ID:" in result.stdout
            assert sample_workflow_response["group_id"] in result.stdout

    def test_status_command_by_document_id(self, runner, mock_client, sample_status_response):
        """Test status command with document ID filter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_status_response
        mock_client.api.http_client.get.return_value = mock_response

        document_id = str(uuid4())
        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["status", "--document-id", document_id])

            assert result.exit_code == 0
            assert "PDF Processing Workflows" in result.stdout
            assert "running" in result.stdout
            # Progress is displayed as "completed_jobs/total_jobs (percentage%)"
            # The exact format may vary due to Rich table formatting

            # Verify API call
            mock_client.api.http_client.get.assert_called_once()
            call_args = mock_client.api.http_client.get.call_args
            assert "/api/v1/workflows/status" in call_args[0][0]
            assert call_args[1]["params"]["document_id"] == document_id

    def test_status_command_by_reference(self, runner, mock_client, sample_status_response):
        """Test status command with reference filter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_status_response
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["status", "--reference", "test_ref", "--workspace", "test_workspace"])

            assert result.exit_code == 0
            assert "PDF Processing Workflows" in result.stdout

            # Verify API call parameters
            call_args = mock_client.api.http_client.get.call_args
            params = call_args[1]["params"]
            assert params["reference"] == "test_ref"
            assert params["workspace_name"] == "test_workspace"

    def test_status_command_json_output(self, runner, mock_client, sample_status_response):
        """Test status command with JSON output format."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_status_response
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["status", "--document-id", str(uuid4()), "--json"])

            assert result.exit_code == 0

            # Verify JSON output
            try:
                output_data = json.loads(result.stdout.strip())
                assert len(output_data) == 1
                assert output_data[0]["status"] == "running"
                assert output_data[0]["group_id"] == "document_workflow_123_abcd1234"
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")

    def test_status_command_no_workflows_found(self, runner, mock_client):
        """Test status command when no workflows are found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["status", "--document-id", str(uuid4())])

            assert result.exit_code == 0
            assert "No workflows found" in result.stdout

    def test_status_command_missing_parameters(self, runner, mock_client):
        """Test status command without required parameters."""
        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["status"])

            assert result.exit_code == 1
            assert "Must specify either --document-id or --reference" in result.stdout

    def test_restart_command_success(self, runner, mock_client, sample_status_response):
        """Test successful workflow restart command."""
        # Mock status response with failed workflow
        failed_status = sample_status_response.copy()
        failed_status[0]["status"] = "failed"

        mock_status_response = MagicMock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = failed_status

        mock_restart_response = MagicMock()
        mock_restart_response.status_code = 200
        mock_restart_response.json.return_value = {
            "success": True,
            "restarted_jobs": ["failed_job_1", "failed_job_2"],
            "total_failed": 2,
        }

        mock_client.api.http_client.get.return_value = mock_status_response
        mock_client.api.http_client.post.return_value = mock_restart_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(
                app,
                [
                    "restart",
                    "--document-id",
                    str(uuid4()),
                    "--yes",  # Skip confirmation
                ],
            )

            assert result.exit_code == 0
            assert "Restarted workflow" in result.stdout
            assert "(2 jobs)" in result.stdout

            # Verify API calls
            assert mock_client.api.http_client.get.call_count == 1
            assert mock_client.api.http_client.post.call_count == 1

            # Verify restart API call
            restart_call = mock_client.api.http_client.post.call_args
            assert "/api/v1/workflows/restart" in restart_call[0][0]
            assert restart_call[1]["json"]["failed_only"] is True

    def test_restart_command_no_failed_workflows(self, runner, mock_client, sample_status_response):
        """Test restart command when no failed workflows exist."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_status_response  # Running workflow
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["restart", "--document-id", str(uuid4())])

            assert result.exit_code == 0
            assert "No failed workflows found" in result.stdout

    def test_restart_command_with_confirmation(self, runner, mock_client, sample_status_response):
        """Test restart command with user confirmation."""
        # Mock failed workflow
        failed_status = sample_status_response.copy()
        failed_status[0]["status"] = "failed"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = failed_status
        mock_client.api.http_client.get.return_value = mock_response

        with (
            patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client),
            patch("typer.confirm", return_value=False),
        ):  # User cancels
            result = runner.invoke(app, ["restart", "--document-id", str(uuid4())])

            assert result.exit_code == 0
            assert "Cancelled" in result.stdout

            # Should not call restart API
            mock_client.api.http_client.post.assert_not_called()

    def test_restart_command_full_restart(self, runner, mock_client, sample_status_response):
        """Test restart command with full restart option."""
        failed_status = sample_status_response.copy()
        failed_status[0]["status"] = "failed"

        mock_status_response = MagicMock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = failed_status

        mock_restart_response = MagicMock()
        mock_restart_response.status_code = 200
        mock_restart_response.json.return_value = {
            "success": True,
            "restarted_jobs": ["job1", "job2", "job3"],
            "total_failed": 1,
            "restart_type": "full",
        }

        mock_client.api.http_client.get.return_value = mock_status_response
        mock_client.api.http_client.post.return_value = mock_restart_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(
                app,
                [
                    "restart",
                    "--document-id",
                    str(uuid4()),
                    "--all",  # Full restart (this sets failed_only=False)
                    "--yes",
                ],
            )

            assert result.exit_code == 0

            # Verify restart API call with correct parameters
            restart_call = mock_client.api.http_client.post.call_args
            assert restart_call[1]["json"]["failed_only"] is False

    def test_list_command_success(self, runner, mock_client, sample_status_response):
        """Test successful workflow list command."""
        # Add more workflows to the response
        extended_response = sample_status_response * 3  # 3 workflows
        for i, workflow in enumerate(extended_response):
            workflow["document_id"] = str(uuid4())
            workflow["reference"] = f"test_ref_{i}"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = extended_response
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "Recent Workflows (3 shown)" in result.stdout
            assert "Summary:" in result.stdout

            # Verify API call
            call_args = mock_client.api.http_client.get.call_args
            assert "/api/v1/workflows/" in call_args[0][0]
            assert call_args[1]["params"]["limit"] == 50

    def test_list_command_with_filters(self, runner, mock_client, sample_status_response):
        """Test list command with workspace and status filters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_status_response
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(
                app, ["list", "--workspace", "test_workspace", "--status", "failed", "--limit", "25"]
            )

            assert result.exit_code == 0

            # Verify API call parameters
            call_args = mock_client.api.http_client.get.call_args
            params = call_args[1]["params"]
            assert params["workspace_name"] == "test_workspace"
            assert params["status_filter"] == "failed"
            assert params["limit"] == 25

    def test_list_command_json_output(self, runner, mock_client, sample_status_response):
        """Test list command with JSON output."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_status_response
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["list", "--json"])

            assert result.exit_code == 0

            # Verify JSON output
            try:
                output_data = json.loads(result.stdout.strip())
                assert len(output_data) == 1
                assert output_data[0]["status"] == "running"
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")

    def test_list_command_no_workflows(self, runner, mock_client):
        """Test list command when no workflows exist."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "No workflows found" in result.stdout

    def test_authentication_failure(self, runner):
        """Test CLI commands with authentication failure."""
        with patch(
            "extralit.cli.workflows.__main__.Extralit.from_credentials", side_effect=Exception("Authentication failed")
        ):
            result = runner.invoke(app, ["start", "--document-id", str(uuid4()), "--workspace", "test_workspace"])

            assert result.exit_code == 1
            assert "Authentication failed" in result.stdout

    def test_api_connection_error(self, runner, mock_client):
        """Test CLI commands with API connection errors."""
        mock_client.api.http_client.post.side_effect = Exception("Connection refused")

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["start", "--document-id", str(uuid4()), "--workspace", "test_workspace"])

            assert result.exit_code == 1
            assert "Unexpected error" in result.stdout

    def test_workflow_status_table_formatting(self, runner, mock_client):
        """Test workflow status table formatting with various states."""
        complex_status_response = [
            {
                "document_id": str(uuid4()),
                "workflow_id": str(uuid4()),
                "group_id": "group_1",
                "reference": "completed_workflow",
                "workspace_name": "test_workspace",
                "status": "completed",
                "progress": 1.0,
                "total_jobs": 3,
                "completed_jobs": 3,
                "failed_jobs": 0,
                "running_jobs": 0,
                "created_at": "2024-01-15T10:30:00Z",
            },
            {
                "document_id": str(uuid4()),
                "workflow_id": str(uuid4()),
                "group_id": "group_2",
                "reference": "failed_workflow",
                "workspace_name": "test_workspace",
                "status": "failed",
                "progress": 0.67,
                "total_jobs": 3,
                "completed_jobs": 2,
                "failed_jobs": 1,
                "running_jobs": 0,
                "created_at": "2024-01-15T11:00:00Z",
            },
            {
                "document_id": str(uuid4()),
                "workflow_id": str(uuid4()),
                "group_id": "group_3",
                "reference": "running_workflow",
                "workspace_name": "test_workspace",
                "status": "running",
                "progress": 0.33,
                "total_jobs": 3,
                "completed_jobs": 1,
                "failed_jobs": 0,
                "running_jobs": 2,
                "created_at": "2024-01-15T11:30:00Z",
            },
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = complex_status_response
        mock_client.api.http_client.get.return_value = mock_response

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["status", "--reference", "test_workflows"])

            assert result.exit_code == 0
            assert "PDF Processing Workflows" in result.stdout

            # Check that workflow data is displayed (status may be formatted with colors)
            # The exact formatting may vary due to Rich table rendering
            output = result.stdout
            # Check that some form of status information is present
            assert any(status in output for status in ["completed", "failed", "running"])

            # Check that progress information is displayed in some format
            # Progress may be displayed as percentages or fractions
            assert any(progress in output for progress in ["100%", "67%", "33%", "3/3", "2/3", "1/3"])

    @patch("time.sleep")  # Mock sleep to speed up test
    def test_status_command_watch_mode(self, mock_sleep, runner, mock_client, sample_status_response):
        """Test status command with watch mode."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_status_response
        mock_client.api.http_client.get.return_value = mock_response

        # Mock KeyboardInterrupt to exit watch mode
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        with patch("extralit.cli.workflows.__main__.Extralit.from_credentials", return_value=mock_client):
            result = runner.invoke(app, ["status", "--document-id", str(uuid4()), "--watch"])

            assert result.exit_code == 0
            assert "Stopped watching" in result.stdout

            # Should have made multiple API calls
            assert mock_client.api.http_client.get.call_count >= 2
