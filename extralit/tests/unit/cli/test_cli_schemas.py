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
from pathlib import Path

from argilla.cli.app import app


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


def test_schemas_help(runner):
    """Test that the schemas command shows help message."""
    result = runner.invoke(app, ["schemas", "--help"])
    assert result.exit_code == 0
    assert "schemas management" in result.stdout.lower()


def test_schemas_upload_command_help(runner):
    """Test the help message for the 'upload' subcommand."""
    result = runner.invoke(app, ["schemas", "upload", "--help"])
    assert result.exit_code == 0
    assert "upload" in result.stdout.lower()


def test_schemas_list_command_help(runner):
    """Test the help message for the 'list' subcommand."""
    result = runner.invoke(app, ["schemas", "list", "--help"])
    assert result.exit_code == 0
    assert "list" in result.stdout.lower()


def test_schemas_delete_command_help(runner):
    """Test the help message for the 'delete' subcommand."""
    result = runner.invoke(app, ["schemas", "delete", "--help"])
    assert result.exit_code == 0
    assert "delete" in result.stdout.lower()


@patch("rich.console.Console.print")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_schemas_list(mock_print, runner):
    """Test the 'list schemas' command functionality."""
    result = runner.invoke(
        app,
        [
            "schemas",
            "list",
            "--workspace",
            "research",
        ],
    )

    assert result.exit_code == 0
    mock_print.assert_called_once()

    # Since we're using mock data, just verify that print was called
    # In a more complete test, we could mock the API call and check the output


@patch("rich.console.Console.print")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_schemas_list_with_versions(mock_print, runner):
    """Test the 'list schemas' command with versions flag."""
    result = runner.invoke(app, ["schemas", "list", "--workspace", "research", "--name", "customer-feedback"])

    assert result.exit_code == 0
    mock_print.assert_called_once()


@patch("rich.console.Console.print")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_schemas_list_with_csv_export(mock_print, runner):
    """Test the 'list schemas' command with CSV export."""
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "schemas",
                "list",
                "--workspace",
                "research",
            ],
        )

        assert result.exit_code == 0
        mock_print.assert_called_once()


@patch("argilla.cli.schemas.upload.upload_schemas")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_schemas_upload(mock_upload_schemas, runner):
    """Test the 'upload schemas' command functionality."""
    # Set up the mock to return a successful result
    mock_upload_schemas.return_value = None  # The function doesn't return anything

    with runner.isolated_filesystem():
        # Create a test directory with schema files
        import os

        os.makedirs("schemas")
        with open("schemas/schema1.json", "w") as f:
            f.write('{"name": "test_schema"}')

        # Call the command with the appropriate parameters
        result = runner.invoke(
            app,
            ["schemas", "upload", "--workspace", "research", "schemas", "--overwrite", "--exclude", "excluded_schema"],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the upload_schemas function was called with the correct parameters
        mock_upload_schemas.assert_called_once()
        args, kwargs = mock_upload_schemas.call_args

        # Check that the context was passed
        assert args[0] is not None
        # Check that the directory path was passed
        assert isinstance(args[1], Path)
        assert str(args[1]).endswith("schemas")
        # Check that overwrite was set to True
        assert args[2] is True
        # Check that exclude was set correctly
        assert args[3] == ["excluded_schema"]


@patch("rich.console.Console.print")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_schemas_delete(mock_print, runner):
    """Test the 'delete schema' command functionality."""
    # Simulate user confirming the deletion
    result = runner.invoke(app, ["schemas", "delete", "--workspace", "research", "schema1"], input="y\n")

    assert result.exit_code == 0
    mock_print.assert_called_once()

    # Verify that Console.print was called
    assert mock_print.called

    # For now, we'll just verify that the command completed successfully
    # In a real test, we would need to mock the API call and verify the response


@patch("rich.console.Console.print")
def test_schemas_delete_nonexistent(mock_print, runner):
    """Test deleting a schema that doesn't exist (should fail)."""
    # Make print raise ValueError to simulate schema not found
    mock_print.side_effect = ValueError("Schema not found")

    result = runner.invoke(app, ["schemas", "delete", "--workspace", "research", "nonexistent_schema"])

    # Should exit with code 1 due to ValueError
    assert result.exit_code == 1
