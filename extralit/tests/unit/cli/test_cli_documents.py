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
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from uuid import UUID

from argilla.cli.app import app
from argilla.cli.documents.add import _parse_authors, _parse_year, _display_import_analysis_results


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


def test_documents_help(runner):
    """Test that the documents command shows help message."""
    result = runner.invoke(app, ["documents", "--help"])
    assert result.exit_code == 0
    assert "documents" in result.stdout.lower()


def test_documents_add_command_help(runner):
    """Test the help message for the 'add' subcommand."""
    result = runner.invoke(app, ["documents", "add", "--help"])
    assert result.exit_code == 0
    assert "add a document" in result.stdout.lower()


def test_documents_list_command_help(runner):
    """Test the help message for the 'list' subcommand."""
    result = runner.invoke(app, ["documents", "list", "--help"])
    assert result.exit_code == 0
    assert "list" in result.stdout.lower()


def test_documents_delete_command_help(runner):
    """Test the help message for the 'delete' subcommand."""
    result = runner.invoke(app, ["documents", "delete", "--help"])
    assert result.exit_code == 0
    assert "delete" in result.stdout.lower()


def test_import_bibtex_help(runner):
    """Test the help message for the 'import-bibtex' subcommand."""
    result = runner.invoke(app, ["documents", "import-bibtex", "--help"])
    assert result.exit_code == 0
    assert "import documents from a bibtex file" in result.stdout.lower()
    assert "--bibtex" in result.stdout
    assert "--pdf-folder" in result.stdout
    assert "--collection" in result.stdout
    assert "--analyze-only" in result.stdout


@patch("argilla.client.Argilla.from_credentials")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="@article{key1, title={Test Title}, author={Author One and Author Two}, year={2025}}",
)
@patch("bibtexparser.load")
def test_import_bibtex_analysis(mock_bibtex_load, mock_file_open, mock_from_credentials, runner):
    """Test the 'import-bibtex' command with analysis only."""
    # Mock the bibtexparser.load function
    mock_bibtex_db = MagicMock()
    mock_bibtex_db.entries = [
        {
            "ID": "key1",
            "title": "Test Title",
            "author": "Author One and Author Two",
            "year": "2025",
            "journal": "Test Journal",
            "doi": "10.1234/test",
        }
    ]
    mock_bibtex_load.return_value = mock_bibtex_db

    # Mock the workspace
    mock_workspace = MagicMock()
    mock_workspace.id = UUID("12345678-1234-5678-1234-567812345678")
    mock_workspace._client.api_url = "http://localhost:8000"

    # Mock the session post response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "documents": {
            "key1": {
                "document_create": {
                    "workspace_id": "12345678-1234-5678-1234-567812345678",
                    "reference": "key1",
                    "doi": "10.1234/test",
                },
                "title": "Test Title",
                "authors": ["Author One", "Author Two"],
                "year": 2025,
                "venue": "Test Journal",
                "associated_files": [],
                "status": "add",
                "existing_document_id": None,
            }
        },
        "summary": {"total_documents": 1, "add_count": 1, "update_count": 0, "skip_count": 0, "failed_count": 0},
    }
    mock_workspace._session.post.return_value = mock_response

    # Mock the client
    mock_client = MagicMock()
    mock_client.workspaces.return_value = mock_workspace
    mock_from_credentials.return_value = mock_client

    # Create a temporary bibtex file
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write("@article{key1, title={Test Title}, author={Author One and Author Two}, year={2025}}")

        # Run the command
        result = runner.invoke(
            app,
            ["documents", "import-bibtex", "--workspace", "test-workspace", "--bibtex", "test.bib", "--analyze-only"],
        )

        # Check the result
        assert result.exit_code == 0
        assert "Import Analysis Summary" in result.stdout
        assert "Document Import Status" in result.stdout
        assert "key1" in result.stdout
        assert "Test Title" in result.stdout
        assert "add" in result.stdout

        # Verify API call
        mock_workspace._session.post.assert_called_once()
        args, kwargs = mock_workspace._session.post.call_args
        assert args[0] == "http://localhost:8000/api/v1/imports/analyze"
        assert "workspace_id" in kwargs["json"]
        assert "documents" in kwargs["json"]
        assert "key1" in kwargs["json"]["documents"]


@patch("argilla.client.Argilla.from_credentials")
@patch("builtins.open", new_callable=mock_open)
@patch("bibtexparser.load")
@patch("pathlib.Path.glob")
@patch("pathlib.Path.stat")
def test_import_bibtex_with_pdf_matching(
    mock_stat, mock_glob, mock_bibtex_load, mock_file_open, mock_from_credentials, runner
):
    """Test the 'import-bibtex' command with PDF matching."""
    # Mock the bibtexparser.load function
    mock_bibtex_db = MagicMock()
    mock_bibtex_db.entries = [
        {
            "ID": "key1",
            "title": "Test Title",
            "author": "Author One and Author Two",
            "year": "2025",
            "journal": "Test Journal",
            "doi": "10.1234/test",
        }
    ]
    mock_bibtex_load.return_value = mock_bibtex_db

    # Mock PDF files
    mock_pdf_file = MagicMock()
    mock_pdf_file.stem = "key1"
    mock_pdf_file.name = "key1.pdf"
    mock_glob.return_value = [mock_pdf_file]

    # Mock file stat
    mock_stat_result = MagicMock()
    mock_stat_result.st_size = 12345
    mock_stat.return_value = mock_stat_result

    # Mock the workspace
    mock_workspace = MagicMock()
    mock_workspace.id = UUID("12345678-1234-5678-1234-567812345678")
    mock_workspace._client.api_url = "http://localhost:8000"

    # Mock the session post response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "documents": {
            "key1": {
                "document_create": {
                    "workspace_id": "12345678-1234-5678-1234-567812345678",
                    "reference": "key1",
                    "doi": "10.1234/test",
                },
                "title": "Test Title",
                "authors": ["Author One", "Author Two"],
                "year": 2025,
                "venue": "Test Journal",
                "associated_files": ["key1.pdf"],
                "status": "add",
                "existing_document_id": None,
            }
        },
        "summary": {"total_documents": 1, "add_count": 1, "update_count": 0, "skip_count": 0, "failed_count": 0},
    }
    mock_workspace._session.post.return_value = mock_response

    # Mock the client
    mock_client = MagicMock()
    mock_client.workspaces.return_value = mock_workspace
    mock_from_credentials.return_value = mock_client

    # Create a temporary bibtex file and PDF folder
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write("@article{key1, title={Test Title}, author={Author One and Author Two}, year={2025}}")

        # Create PDF folder
        Path("pdfs").mkdir()

        # Run the command
        result = runner.invoke(
            app,
            [
                "documents",
                "import-bibtex",
                "--workspace",
                "test-workspace",
                "--bibtex",
                "test.bib",
                "--pdf-folder",
                "pdfs",
                "--analyze-only",
            ],
        )

        # Check the result
        assert result.exit_code == 0
        assert "Import Analysis Summary" in result.stdout
        assert "Document Import Status" in result.stdout
        assert "key1" in result.stdout
        assert "Test Title" in result.stdout
        assert "add" in result.stdout

        # Verify API call
        mock_workspace._session.post.assert_called_once()
        args, kwargs = mock_workspace._session.post.call_args
        assert args[0] == "http://localhost:8000/api/v1/imports/analyze"
        assert "workspace_id" in kwargs["json"]
        assert "documents" in kwargs["json"]
        assert "key1" in kwargs["json"]["documents"]
        assert "associated_files" in kwargs["json"]["documents"]["key1"]
        assert len(kwargs["json"]["documents"]["key1"]["associated_files"]) == 1
        assert kwargs["json"]["documents"]["key1"]["associated_files"][0]["filename"] == "key1.pdf"


@patch("argilla.client.Argilla.from_credentials")
def test_import_bibtex_workspace_not_found(mock_from_credentials, runner):
    """Test the 'import-bibtex' command with a non-existent workspace."""
    # Mock the client to return None for workspace
    mock_client = MagicMock()
    mock_client.workspaces.return_value = None
    mock_from_credentials.return_value = mock_client

    # Run the command
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write("@article{key1, title={Test Title}, author={Author One}, year={2025}}")

        result = runner.invoke(
            app, ["documents", "import-bibtex", "--workspace", "nonexistent-workspace", "--bibtex", "test.bib"]
        )

        # Check the result
        assert result.exit_code == 1
        assert "Workspace 'nonexistent-workspace' not found" in result.stdout


@patch("argilla.client.Argilla.from_credentials")
@patch("builtins.open", side_effect=Exception("Error reading file"))
def test_import_bibtex_file_error(mock_open, mock_from_credentials, runner):
    """Test the 'import-bibtex' command with a file error."""
    # Mock the client
    mock_client = MagicMock()
    mock_workspace = MagicMock()
    mock_client.workspaces.return_value = mock_workspace
    mock_from_credentials.return_value = mock_client

    # Run the command
    result = runner.invoke(
        app, ["documents", "import-bibtex", "--workspace", "test-workspace", "--bibtex", "nonexistent.bib"]
    )

    # Check the result
    assert result.exit_code == 1
    assert "Error importing documents" in result.stdout


@patch("argilla.client.Argilla.from_credentials")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="@article{key1, title={Test Title}, author={Author One}, year={2025}}",
)
@patch("bibtexparser.load")
@patch("argilla.cli.documents.add._display_import_analysis_results")
def test_import_bibtex_api_error(mock_display, mock_bibtex_load, mock_file_open, mock_from_credentials, runner):
    """Test the 'import-bibtex' command with an API error."""
    # Mock the bibtexparser.load function
    mock_bibtex_db = MagicMock()
    mock_bibtex_db.entries = [
        {
            "ID": "key1",
            "title": "Test Title",
            "author": "Author One",
            "year": "2025",
        }
    ]
    mock_bibtex_load.return_value = mock_bibtex_db

    # Mock the workspace
    mock_workspace = MagicMock()
    mock_workspace.id = UUID("12345678-1234-5678-1234-567812345678")
    mock_workspace._client.api_url = "http://localhost:8000"

    # Mock the session post response to return an error
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"detail": "Validation error"}
    mock_workspace._session.post.return_value = mock_response

    # Mock the client
    mock_client = MagicMock()
    mock_client.workspaces.return_value = mock_workspace
    mock_from_credentials.return_value = mock_client

    # Run the command
    with runner.isolated_filesystem():
        result = runner.invoke(
            app, ["documents", "import-bibtex", "--workspace", "test-workspace", "--bibtex", "test.bib"]
        )

        # Check the result
        assert result.exit_code == 1
        assert "Error importing documents" in result.stdout
        assert "Error analyzing import: Validation error" in result.stdout


def test_parse_authors():
    """Test the _parse_authors function."""
    # Test with empty string
    assert _parse_authors("") == []

    # Test with single author
    assert _parse_authors("John Doe") == ["John Doe"]

    # Test with multiple authors
    assert _parse_authors("John Doe and Jane Smith") == ["John Doe", "Jane Smith"]

    # Test with braces
    assert _parse_authors("{John Doe} and {Jane Smith}") == ["John Doe", "Jane Smith"]


def test_parse_year():
    """Test the _parse_year function."""
    # Test with empty string
    assert _parse_year("") is None

    # Test with valid year
    assert _parse_year("2025") == 2025

    # Test with invalid year
    assert _parse_year("not a year") is None


@patch("rich.table.Table.add_row")
@patch("rich.console.Console.print")
def test_display_import_analysis_results(mock_print, mock_add_row):
    """Test the _display_import_analysis_results function."""
    # Create a mock console
    console = MagicMock()

    # Create a mock analysis result
    analysis_result = {
        "documents": {
            "key1": {
                "title": "Test Title",
                "authors": ["Author One", "Author Two"],
                "status": "add",
                "associated_files": ["file1.pdf", "file2.pdf"],
            }
        },
        "summary": {"total_documents": 1, "add_count": 1, "update_count": 0, "skip_count": 0, "failed_count": 0},
    }

    # Call the function
    _display_import_analysis_results(console, analysis_result)

    # Verify that console.print was called twice (once for each table)
    assert console.print.call_count == 2
