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


def test_extraction_help(runner):
    """Test that the extraction command shows help message."""
    result = runner.invoke(app, ["extraction", "--help"])
    assert result.exit_code == 0
    assert "data extraction operations." in result.stdout.lower()


@pytest.mark.skip(reason="Test temporarily disabled")
def test_extraction_export_command_help(runner):
    """Test the help message for the 'export' subcommand."""
    result = runner.invoke(app, ["extraction", "export", "--help"])
    assert result.exit_code == 0
    assert "Export extraction data" in result.stdout.lower()


@pytest.mark.skip(reason="Test temporarily disabled")
@patch("rich.console.Console.print")
@patch("time.sleep")  # Mock sleep to speed up the test
def test_extraction_export_basic(mock_sleep, mock_print, runner):
    """Test basic extraction export command functionality."""
    result = runner.invoke(
        app, ["extraction", "--workspace", "research", "--env-file", ".env.test", "export", "--output", "exports"]
    )

    assert result.exit_code == 0

    # Verify that sleep was called to simulate export process
    mock_sleep.assert_called_once()

    # Verify that Console.print was called multiple times
    assert mock_print.call_count >= 2

    # Verify that the command completed successfully
    # We can't easily check the content of the Panel object, so we'll just verify
    # that the command completed successfully and the expected functions were called


@patch("rich.console.Console.print")
@patch("time.sleep")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_extraction_export_with_type(mock_sleep, mock_print, runner):
    """Test extraction export command with type option."""
    result = runner.invoke(
        app,
        [
            "extraction",
            "--workspace",
            "research",
            "--env-file",
            ".env.test",
            "export",
            "--type",
            "text_classification",
            "--output",
            "exports",
        ],
    )

    assert result.exit_code == 0

    # Verify that sleep was called to simulate export process
    mock_sleep.assert_called_once()

    # Verify that Console.print was called multiple times
    assert mock_print.call_count >= 2

    # Verify that the command completed successfully
    # We can't easily check the content of the Panel object, so we'll just verify
    # that the command completed successfully and the expected functions were called


@patch("rich.console.Console.print")
@patch("time.sleep")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_extraction_export_with_different_type(mock_sleep, mock_print, runner):
    """Test extraction export command with a different type."""
    result = runner.invoke(
        app,
        [
            "extraction",
            "--workspace",
            "research",
            "--env-file",
            ".env.test",
            "export",
            "--type",
            "feedback",
            "--output",
            "custom-exports",
        ],
    )

    assert result.exit_code == 0

    # Verify that sleep was called to simulate export process
    mock_sleep.assert_called_once()

    # Verify that Console.print was called multiple times
    assert mock_print.call_count >= 2

    # Verify that the command completed successfully
    # We can't easily check the content of the Panel object, so we'll just verify
    # that the command completed successfully and the expected functions were called


@patch("rich.console.Console.print")
def test_extraction_export_missing_workspace(mock_print, runner):
    """Test extraction export command without workspace (should fail)."""
    # Mock print to capture the error message
    mock_print.side_effect = lambda x: None

    result = runner.invoke(app, ["extraction", "--env-file", ".env.test", "export", "--output", "exports"])

    # Should exit with non-zero code due to missing workspace
    assert result.exit_code != 0


@patch("rich.console.Console.print")
def test_extraction_export_missing_env_file(mock_print, runner):
    """Test extraction export command without env file (should fail)."""
    # Mock print to capture the error message
    mock_print.side_effect = lambda x: None

    result = runner.invoke(app, ["extraction", "--workspace", "research", "export", "--output", "exports"])

    # Should exit with non-zero code due to missing env file
    assert result.exit_code != 0


@patch("rich.console.Console.print")
def test_extraction_export_nonexistent_dataset(mock_print, runner):
    """Test exporting a nonexistent dataset (should fail)."""
    # Make print raise ValueError to simulate dataset not found
    mock_print.side_effect = ValueError("Dataset not found")

    result = runner.invoke(
        app,
        [
            "extraction",
            "--workspace",
            "research",
            "--env-file",
            ".env.test",
            "export",
            "--type",
            "nonexistent_type",
            "--output",
            "exports",
        ],
    )

    # Should exit with code 1 due to ValueError
    assert result.exit_code == 1
