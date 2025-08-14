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

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from extralit.cli.app import app


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@patch("extralit.client.Extralit.from_credentials")
@patch("extralit.cli.documents.import_bib._validate_workspace_and_folder")
@patch("extralit.cli.documents.import_bib._parse_bibtex_to_dataframe")
@patch("extralit.cli.documents.import_bib._match_pdfs_to_dataframe")
@patch("extralit.cli.documents.import_bib._send_import_analysis_request")
@patch("extralit.cli.documents.import_bib._display_import_analysis_results")
def test_import_bibtex_analysis(
    mock_display, mock_analysis, mock_match_pdfs, mock_parse_bib, mock_validate, mock_from_credentials, runner
):
    """Test the 'import' command with analysis only."""
    # Mock client and workspace
    mock_client = MagicMock()
    mock_workspace = MagicMock()
    mock_workspace.id = "workspace-uuid"
    mock_from_credentials.return_value = mock_client
    mock_validate.return_value = mock_workspace

    # Mock DataFrame parsing
    import pandas as pd

    mock_df = pd.DataFrame([{"reference": "key1", "title": "Test Title", "files": ""}])
    mock_parse_bib.return_value = mock_df
    mock_match_pdfs.return_value = mock_df

    # Mock analysis response
    mock_analysis_result = {
        "documents": {"key1": {"status": "add", "associated_files": []}},
        "summary": {"total_documents": 1, "add_count": 1, "update_count": 0, "skip_count": 0, "failed_count": 0},
    }
    mock_analysis.return_value = mock_analysis_result

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


@patch("extralit.client.Extralit.from_credentials")
@patch("extralit.cli.documents.import_bib._validate_workspace_and_folder")
@patch("extralit.cli.documents.import_bib._parse_bibtex_to_dataframe")
@patch("extralit.cli.documents.import_bib._match_pdfs_to_dataframe")
@patch("extralit.cli.documents.import_bib._send_import_analysis_request")
@patch("extralit.cli.documents.import_bib._display_import_analysis_results")
def test_import_bibtex_with_pdf_matching(
    mock_display, mock_analysis, mock_match_pdfs, mock_parse_bib, mock_validate, mock_from_credentials, runner
):
    """Test the 'import' command with PDF matching."""
    # Mock client and workspace
    mock_client = MagicMock()
    mock_workspace = MagicMock()
    mock_workspace.id = "workspace-uuid"
    mock_from_credentials.return_value = mock_client
    mock_validate.return_value = mock_workspace

    # Mock DataFrame parsing and PDF matching
    import pandas as pd

    mock_df_initial = pd.DataFrame(
        [
            {"reference": "key1", "title": "Test Title", "files": ""},
            {"reference": "key2", "title": "Another Title", "files": ""},
        ]
    )
    mock_df_matched = pd.DataFrame(
        [
            {"reference": "key1", "title": "Test Title", "files": "pdfs/key1.pdf"},
            {"reference": "key2", "title": "Another Title", "files": "pdfs/key2_paper.pdf"},
        ]
    )
    mock_parse_bib.return_value = mock_df_initial
    mock_match_pdfs.return_value = mock_df_matched

    # Mock analysis response
    mock_analysis_result = {
        "documents": {
            "key1": {"status": "add", "associated_files": ["key1.pdf"]},
            "key2": {"status": "add", "associated_files": ["key2_paper.pdf"]},
        },
        "summary": {"total_documents": 2, "add_count": 2, "update_count": 0, "skip_count": 0, "failed_count": 0},
    }
    mock_analysis.return_value = mock_analysis_result

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
    # Verify that PDF matching was called
    mock_match_pdfs.assert_called_once()


def test_import_bibtex_file_error(runner):
    """Test the 'import' command with a file error."""
    with runner.isolated_filesystem():
        Path("pdfs").mkdir()
        result = runner.invoke(
            app, ["documents", "import", "--workspace", "test-workspace", "--bibtex", "nonexistent.bib", "pdfs"]
        )
    # Typer returns exit code 2 for usage errors (file not found, etc.)
    assert result.exit_code == 2
    assert "nonexistent.bib" in result.output or "does not exist" in result.output


@patch("extralit.client.Extralit.from_credentials")
@patch("extralit.cli.documents.import_bib._validate_workspace_and_folder")
@patch("extralit.cli.documents.import_bib._parse_bibtex_to_dataframe")
def test_import_bibtex_api_error(mock_parse_bib, mock_validate, mock_from_credentials, runner):
    """Test the 'import' command with an API error."""
    # Mock client and workspace
    mock_client = MagicMock()
    mock_workspace = MagicMock()
    mock_workspace.id = "workspace-uuid"
    mock_from_credentials.return_value = mock_client
    mock_validate.return_value = mock_workspace

    # Simulate API error by raising ValueError in parsing
    mock_parse_bib.side_effect = ValueError("Error analyzing import: Validation error")

    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write("@article{key1, title={Test Title}, author={Author One}, year={2025}}")
        Path("pdfs").mkdir()
        result = runner.invoke(
            app, ["documents", "import", "--workspace", "test-workspace", "--bibtex", "test.bib", "pdfs"]
        )
    # Application error should return exit code 1
    assert result.exit_code == 1
    assert "error" in result.stdout.lower() or "error" in result.output.lower()


def test_display_import_analysis_results():
    """Test the _display_import_analysis_results function."""
    from io import StringIO

    from rich.console import Console

    from extralit.cli.documents.import_bib import _display_import_analysis_results

    # Create a console that captures output
    output = StringIO()
    console = Console(file=output, width=80)

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

    # Verify that output was generated (tables were printed)
    output_str = output.getvalue()
    assert "Import Analysis Summary" in output_str
    assert "Document Import Status" in output_str


@patch("extralit.client.Extralit.from_credentials")
@patch("extralit.cli.documents.import_bib._validate_workspace_and_folder")
@patch("extralit.cli.documents.import_bib._parse_bibtex_to_dataframe")
@patch("extralit.cli.documents.import_bib._match_pdfs_to_dataframe")
@patch("extralit.cli.documents.import_bib._send_import_analysis_request")
@patch("extralit.cli.documents.import_bib._display_import_analysis_results")
def test_import_bibtex_filename_matching(
    mock_display, mock_analysis, mock_match_pdfs, mock_parse_bib, mock_validate, mock_from_credentials, runner
):
    """Test the filename matching in the import_bibtex function."""
    # Mock client and workspace
    mock_client = MagicMock()
    mock_workspace = MagicMock()
    mock_workspace.id = "workspace-uuid"
    mock_from_credentials.return_value = mock_client
    mock_validate.return_value = mock_workspace

    # Mock DataFrame parsing and PDF matching
    import pandas as pd

    mock_df_initial = pd.DataFrame(
        [
            {"reference": "key1", "title": "Test Title", "files": ""},
            {"reference": "key2", "title": "Another Title", "files": ""},
            {"reference": "key3", "title": "Third Title", "files": ""},
        ]
    )
    mock_df_matched = pd.DataFrame(
        [
            {"reference": "key1", "title": "Test Title", "files": "pdfs/key1.pdf"},
            {"reference": "key2", "title": "Another Title", "files": "pdfs/paper_key2.pdf"},
            {"reference": "key3", "title": "Third Title", "files": "pdfs/key3_2023.pdf"},
        ]
    )
    mock_parse_bib.return_value = mock_df_initial
    mock_match_pdfs.return_value = mock_df_matched

    # Mock analysis response
    mock_analysis_result = {
        "documents": {
            "key1": {"status": "add", "associated_files": ["key1.pdf"]},
            "key2": {"status": "add", "associated_files": ["paper_key2.pdf"]},
            "key3": {"status": "add", "associated_files": ["key3_2023.pdf"]},
        },
        "summary": {"total_documents": 3, "add_count": 3, "update_count": 0, "skip_count": 0, "failed_count": 0},
    }
    mock_analysis.return_value = mock_analysis_result

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
    # Verify that PDF matching was called with the parsed DataFrame
    mock_match_pdfs.assert_called_once()
