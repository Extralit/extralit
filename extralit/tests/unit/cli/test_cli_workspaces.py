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

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from argilla.cli.app import app


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


def test_workspaces_help(runner):
    """Test that the workspaces command shows help message."""
    result = runner.invoke(app, ["workspaces", "--help"])
    assert result.exit_code == 0
    assert "workspace" in result.stdout


@pytest.mark.skip(reason="Test temporarily disabled")
def test_workspaces_list_command_help(runner):
    """Test the help message for the 'list' subcommand."""
    result = runner.invoke(app, ["workspaces", "list", "--help"])
    assert result.exit_code == 0
    assert "Lists workspaces of the logged user" in result.stdout


@pytest.mark.skip(reason="Test temporarily disabled")
def test_workspaces_create_command_help(runner):
    """Test the help message for the 'create' subcommand."""
    result = runner.invoke(app, ["workspaces", "create", "--help"])
    assert result.exit_code == 0
    assert "Create a workspace" in result.stdout


@pytest.mark.skip(reason="Test temporarily disabled")
def test_workspaces_add_user_command_help(runner):
    """Test the help message for the 'add-user' subcommand."""
    result = runner.invoke(app, ["workspaces", "--name", "default", "add-user", "--help"])
    assert result.exit_code == 0
    assert "Adds a user to a workspace" in result.stdout


@pytest.mark.skip(reason="Test temporarily disabled")
def test_workspaces_delete_user_command_help(runner):
    """Test the help message for the 'delete-user' subcommand."""
    result = runner.invoke(app, ["workspaces", "--name", "default", "delete-user", "--help"])
    assert result.exit_code == 0
    assert "Deletes a user from a workspace" in result.stdout


@patch("argilla.cli.workspaces.__main__.get_workspaces")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_workspaces_list(mock_get_workspaces, runner):
    """Test the 'list' command functionality."""
    # Import datetime here to avoid circular imports
    from datetime import datetime

    # Mock the get_workspaces function to return test data with proper datetime objects
    mock_get_workspaces.return_value = [
        {
            "id": "1",
            "name": "default",
            "inserted_at": datetime(2025, 4, 10, 10, 0, 0),
            "updated_at": datetime(2025, 4, 10, 10, 0, 0),
        },
        {
            "id": "2",
            "name": "research",
            "inserted_at": datetime(2025, 4, 12, 15, 30, 45),
            "updated_at": datetime(2025, 4, 12, 15, 30, 45),
        },
    ]

    result = runner.invoke(app, ["workspaces", "list"])
    assert result.exit_code == 0
    assert "default" in result.stdout
    assert "research" in result.stdout
    mock_get_workspaces.assert_called_once()


@pytest.mark.skip(reason="Test temporarily disabled")
def test_workspaces_create(runner):
    """Test the 'create' command functionality."""
    # We don't need to mock here as the create_workspace function is defined within the module
    # and doesn't make external API calls in the test environment

    result = runner.invoke(app, ["workspaces", "create", "test-workspace"])
    assert result.exit_code == 0
    assert "test-workspace" in result.stdout
    assert "successfully created" in result.stdout.lower()


@pytest.mark.skip(reason="Test temporarily disabled")
@patch("argilla.cli.workspaces.__main__.get_workspace")
@patch("argilla.cli.workspaces.__main__.get_user")
def test_workspaces_add_user(mock_get_user, mock_get_workspace, runner):
    """Test the 'add-user' command functionality."""
    # Mock the workspace and user retrieval functions
    mock_get_workspace.return_value = {
        "id": "2",
        "name": "research",
        "inserted_at": "2025-04-12 15:30:45",
        "updated_at": "2025-04-12 15:30:45",
    }

    # Mock a non-owner user
    mock_get_user.return_value = {"id": "3", "username": "annotator", "role": "annotator", "is_owner": False}

    result = runner.invoke(app, ["workspaces", "--name", "research", "add-user", "annotator"])

    assert result.exit_code == 0
    assert "annotator" in result.stdout
    assert "research" in result.stdout
    assert "added" in result.stdout.lower()
    mock_get_workspace.assert_called_once_with("research")
    mock_get_user.assert_called_once_with("annotator")


@pytest.mark.skip(reason="Test temporarily disabled")
@patch("argilla.cli.workspaces.__main__.get_workspace")
@patch("argilla.cli.workspaces.__main__.get_user")
def test_workspaces_delete_user(mock_get_user, mock_get_workspace, runner):
    """Test the 'delete-user' command functionality."""
    # Mock the workspace and user retrieval functions
    mock_get_workspace.return_value = {
        "id": "2",
        "name": "research",
        "inserted_at": "2025-04-12 15:30:45",
        "updated_at": "2025-04-12 15:30:45",
    }

    # Mock a non-owner user
    mock_get_user.return_value = {"id": "3", "username": "annotator", "role": "annotator", "is_owner": False}

    result = runner.invoke(app, ["workspaces", "--name", "research", "delete-user", "annotator"])

    assert result.exit_code == 0
    assert "annotator" in result.stdout
    assert "research" in result.stdout
    assert "removed" in result.stdout.lower()
    mock_get_workspace.assert_called_once_with("research")
    mock_get_user.assert_called_once_with("annotator")
