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
from unittest.mock import patch, MagicMock
from pathlib import Path

from argilla.cli.app import app
from argilla.cli.documents.import_bib import _parse_authors, _parse_year, _display_import_analysis_results


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
    """Test the help message for the 'import' subcommand."""
    result = runner.invoke(app, ["documents", "import", "--help"])
    assert result.exit_code == 0
    assert "import documents from a bibtex file" in result.stdout.lower()
    assert "--bibtex" in result.stdout
    assert "pdf_folder" in result.stdout  # positional argument
    assert "--collection" in result.stdout
    assert "--dry-run" in result.stdout


@patch("argilla.client.Argilla.from_credentials")
@patch(
    "builtins.open",
    new_callable=MagicMock,
    read_data="@article{key1, title={Test Title}, author={Author One and Author Two}, year={2025}}",
)
@patch("bibtexparser.load")
def test_import_bibtex_analysis(mock_bibtex_load, mock_file_open, mock_from_credentials, runner):
    """Test the 'import' command with analysis only."""
    # Mock bibtex parser to return entries with reference keys
    mock_bibtex_db = MagicMock()
    mock_bibtex_db.entries = [
        {"ID": "key1", "title": "Test Title", "author": "Author One and Author Two", "year": "2025"},
    ]
    mock_bibtex_load.return_value = mock_bibtex_db
    # Run the command
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write("@article{key1, title={Test Title}, author={Author One and Author Two}, year={2025}}")
        Path("pdfs").mkdir()
        result = runner.invoke(
            app,
            [
                "documents",
                "import",
                "--workspace",
                "test-workspace",
                "--bibtex",
                "test.bib",
                "pdfs",  # positional argument
                "--dry-run",
            ],
        )
    assert result.exit_code == 0
    assert "import analysis complete" in result.stdout.lower()


@patch("argilla.client.Argilla.from_credentials")
@patch("builtins.open", new_callable=MagicMock)
@patch("bibtexparser.load")
@patch("pathlib.Path.glob")
@patch("pathlib.Path.stat")
@patch("pathlib.Path.rglob")
def test_import_bibtex_with_pdf_matching(
    mock_rglob, mock_stat, mock_glob, mock_bibtex_load, mock_file_open, mock_from_credentials, runner
):
    """Test the 'import' command with PDF matching."""
    # Mock bibtex parser to return entries with reference keys
    mock_bibtex_db = MagicMock()
    mock_bibtex_db.entries = [
        {"ID": "key1", "title": "Test Title", "author": "Author One and Author Two", "year": "2025"},
        {"ID": "key2", "title": "Another Title", "author": "Author Three", "year": "2024"},
    ]
    mock_bibtex_load.return_value = mock_bibtex_db
    # Mock PDF files that match reference keys
    mock_pdf_files = [
        MagicMock(name="pdfs/key1.pdf", stem="key1"),
        MagicMock(name="pdfs/key2_paper.pdf", stem="key2_paper"),
        MagicMock(name="pdfs/unmatched.pdf", stem="unmatched"),
    ]
    mock_rglob.return_value = mock_pdf_files
    # Mock file stats to return file sizes
    mock_stat.return_value.st_size = 1024
    Path("pdfs")
    # Run the command
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write("@article{key1, title={Test Title}, author={Author One and Author Two}, year={2025}}")
        Path("pdfs").mkdir()
        result = runner.invoke(
            app,
            [
                "documents",
                "import",
                "--workspace",
                "test-workspace",
                "--bibtex",
                "test.bib",
                "pdfs",  # positional argument
                "--dry-run",
            ],
        )
    assert result.exit_code == 0
    assert "import analysis complete" in result.stdout.lower()
    mock_rglob.assert_called_with("*.pdf")


@patch("argilla.client.Argilla.from_credentials")
@patch("builtins.open", side_effect=Exception("Error reading file"))
def test_import_bibtex_file_error(mock_open, mock_from_credentials, runner):
    """Test the 'import' command with a file error."""
    with runner.isolated_filesystem():
        Path("pdfs").mkdir()
        result = runner.invoke(
            app, ["documents", "import", "--workspace", "test-workspace", "--bibtex", "nonexistent.bib", "pdfs"]
        )
    # Typer returns exit code 2 for usage errors (file not found, etc.)
    assert result.exit_code == 2
    assert "nonexistent.bib" in result.output or "does not exist" in result.output


@patch("argilla.client.Argilla.from_credentials")
@patch(
    "builtins.open",
    new_callable=MagicMock,
    read_data="@article{key1, title={Test Title}, author={Author One}, year={2025}}",
)
@patch("bibtexparser.load")
@patch("argilla.cli.documents.add._display_import_analysis_results")
def test_import_bibtex_api_error(mock_display, mock_bibtex_load, mock_file_open, mock_from_credentials, runner):
    """Test the 'import' command with an API error."""
    # Simulate API error by raising ValueError in analysis
    mock_bibtex_load.side_effect = ValueError("Error analyzing import: Validation error")
    with runner.isolated_filesystem():
        Path("pdfs").mkdir()
        result = runner.invoke(
            app, ["documents", "import", "--workspace", "test-workspace", "--bibtex", "test.bib", "pdfs"]
        )
    # Application error should return exit code 1
    assert result.exit_code == 1
    assert "error" in result.stdout.lower() or "error" in result.output.lower()


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


@patch("argilla.client.Argilla.from_credentials")
@patch("builtins.open", new_callable=MagicMock)
@patch("bibtexparser.load")
@patch("pathlib.Path.rglob")
@patch("pathlib.Path.stat")
@patch("requests.post")
def test_import_bibtex_filename_matching(
    mock_post, mock_stat, mock_rglob, mock_bibtex_load, mock_file_open, mock_from_credentials, runner
):
    """Test the filename matching in the import_bibtex function."""
    # Mock client
    mock_client = MagicMock()
    mock_workspace = MagicMock()
    mock_workspace.id = "workspace-uuid"
    mock_client.workspaces.return_value = mock_workspace
    mock_from_credentials.return_value = mock_client
    # Mock bibtex parser to return entries with reference keys
    mock_bibtex_db = MagicMock()
    mock_bibtex_db.entries = [
        {"ID": "key1", "title": "Test Title", "author": "Author One", "year": "2025"},
        {"ID": "key2", "title": "Another Title", "author": "Author Two", "year": "2024"},
        {"ID": "key3", "title": "Third Title", "author": "Author Three", "year": "2023"},
    ]
    mock_bibtex_load.return_value = mock_bibtex_db
    # Mock PDF files with different naming patterns
    mock_pdf_files = [
        MagicMock(name="pdfs/key1.pdf", stem="key1"),  # Exact match
        MagicMock(name="pdfs/paper_key2.pdf", stem="paper_key2"),  # Partial match
        MagicMock(name="pdfs/key3_2023.pdf", stem="key3_2023"),  # Partial match with year
        MagicMock(name="pdfs/unmatched.pdf", stem="unmatched"),  # No match
    ]
    mock_rglob.return_value = mock_pdf_files
    # Mock file stats to return file sizes
    mock_stat.return_value.st_size = 1024
    # Mock API response for analysis
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "documents": {
            "key1": {"status": "add", "associated_files": ["key1.pdf"]},
            "key2": {"status": "add", "associated_files": ["paper_key2.pdf"]},
            "key3": {"status": "add", "associated_files": ["key3_2023.pdf"]},
        },
        "summary": {"total_documents": 3, "add_count": 3, "update_count": 0, "skip_count": 0, "failed_count": 0},
    }
    mock_post.return_value = mock_response
    # Run the command
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write("@article{key1, title={Test Title}, author={Author One}, year={2025}}")
        Path("pdfs").mkdir()
        result = runner.invoke(
            app,
            [
                "documents",
                "import",
                "--workspace",
                "test-workspace",
                "--bibtex",
                "test.bib",
                "pdfs",
                "--dry-run",
            ],
        )
    assert result.exit_code == 0
    assert "import analysis complete" in result.stdout.lower()
    # Check that the file matching worked correctly in the output (at least one file per key)
    for key in ["key1", "key2", "key3"]:
        assert key in result.stdout or key in result.output
