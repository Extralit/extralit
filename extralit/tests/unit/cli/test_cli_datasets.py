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


def test_datasets_help(runner):
    """Test that the datasets command shows help message."""
    result = runner.invoke(app, ["datasets", "--help"])
    assert result.exit_code == 0
    assert "Commands for dataset management" in result.stdout


def test_datasets_list_command_help(runner):
    """Test the help message for the 'list' subcommand."""
    result = runner.invoke(app, ["datasets", "list", "--help"])
    assert result.exit_code == 0
    assert "List datasets" in result.stdout


def test_datasets_create_command_help(runner):
    """Test the help message for the 'create' subcommand."""
    result = runner.invoke(app, ["datasets", "create", "--help"])
    assert result.exit_code == 0
    assert "Creates a new dataset" in result.stdout


def test_datasets_delete_command_help(runner):
    """Test the help message for the 'delete' subcommand."""
    result = runner.invoke(app, ["datasets", "delete", "--help"])
    assert result.exit_code == 0
    assert "Deletes a dataset" in result.stdout


def test_datasets_push_to_hf_command_help(runner):
    """Test the help message for the 'push-to-huggingface' subcommand."""
    result = runner.invoke(app, ["datasets", "push-to-huggingface", "--help"])
    assert result.exit_code == 0
    assert "Push a dataset to HuggingFace Hub" in result.stdout


@patch("argilla.cli.datasets.__main__.list_datasets")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_datasets_list(mock_list_datasets, runner):
    """Test the 'list' command functionality."""
    # Mock the list_datasets function to return test data
    mock_list_datasets.return_value = [
        {
            "id": "dataset1",
            "name": "sentiment-analysis",
            "workspace": "research",
            "type": "text_classification",
            "created_at": "2025-04-10 10:00:00",
            "updated_at": "2025-04-10 10:00:00",
        },
        {
            "id": "dataset2",
            "name": "named-entity-recognition",
            "workspace": "default",
            "type": "token_classification",
            "created_at": "2025-04-12 15:30:45",
            "updated_at": "2025-04-12 15:30:45",
        },
    ]

    result = runner.invoke(app, ["datasets", "list", "--workspace", "research"])
    assert result.exit_code == 0
    assert "sentiment-analysis" in result.stdout
    assert "named-entity-recognition" in result.stdout
    assert "research" in result.stdout
    assert "default" in result.stdout
    mock_list_datasets.assert_called_once()


@patch("argilla.cli.datasets.__main__.create_dataset")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_datasets_create(mock_create_dataset, runner):
    """Test the 'create' command functionality."""
    # Mock the create_dataset function
    mock_create_dataset.return_value = {
        "id": "new-dataset",
        "name": "test-dataset",
        "workspace": "research",
        "type": "text_classification",
        "tags": [],
        "created_at": "2025-04-14 12:00:00",
        "updated_at": "2025-04-14 12:00:00",
    }

    result = runner.invoke(
        app,
        ["datasets", "create", "--name", "test-dataset", "--workspace", "research", "--type", "text_classification"],
    )

    assert result.exit_code == 0
    assert "Dataset created" in result.stdout
    assert "test-dataset" in result.stdout
    assert "research" in result.stdout
    mock_create_dataset.assert_called_once()


@patch("argilla.cli.datasets.__main__.delete_dataset")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_datasets_delete(mock_delete_dataset, runner):
    """Test the 'delete' command functionality."""
    # Mock the delete_dataset function
    mock_delete_dataset.return_value = True

    # Mock user confirmation
    with patch("typer.confirm", return_value=True):
        result = runner.invoke(
            app,
            [
                "datasets",
                "delete",
                "--name",
                "test-dataset",
                "--workspace",
                "research",
            ],
        )

    assert result.exit_code == 0
    assert "Dataset deleted" in result.stdout
    assert "test-dataset" in result.stdout
    mock_delete_dataset.assert_called_once()


@patch("argilla.cli.datasets.__main__.push_to_huggingface")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_datasets_push_to_hf(mock_push_to_hf, runner):
    """Test the 'push-to-huggingface' command functionality."""
    # Mock the push_to_huggingface function
    mock_push_to_hf.return_value = {"dataset": "test-dataset", "hf_repo": "username/test-dataset", "status": "success"}

    result = runner.invoke(
        app,
        [
            "datasets",
            "push-to-huggingface",
            "--name",
            "test-dataset",
            "--workspace",
            "research",
            "--repo-id",
            "username/test-dataset",
            "--private",
        ],
    )

    assert result.exit_code == 0
    assert "Dataset pushed to HuggingFace" in result.stdout
    assert "username/test-dataset" in result.stdout
    mock_push_to_hf.assert_called_once()
