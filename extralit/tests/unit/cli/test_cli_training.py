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
from argilla.cli.training.__main__ import Framework


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


def test_training_help(runner):
    """Test that the training command shows help message."""
    result = runner.invoke(app, ["training", "--help"])
    assert result.exit_code == 0
    assert "trainer" in result.stdout.lower()


@patch("argilla.cli.training.__main__.framework_callback")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_training_framework_validation(mock_framework_callback, runner):
    """Test that the framework parameter is validated correctly."""
    # Set up the mock to return a valid framework
    mock_framework_callback.return_value = Framework.SPACY

    # Valid framework
    result = runner.invoke(app, ["training", "--framework", "spacy", "--help"])
    assert result.exit_code == 0

    # Verify that the framework_callback was called with the correct value
    mock_framework_callback.assert_called_with("spacy")


@patch("rich.console.Console.print")
@patch("argilla.cli.training.__main__.framework_callback")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_training_basic(mock_framework_callback, mock_print, runner):
    """Test basic training command functionality."""
    # Set up the mock to return a valid framework
    mock_framework_callback.return_value = Framework.SPACY

    result = runner.invoke(
        app, ["training", "--name", "test_dataset", "--framework", "spacy", "--model", "en_core_web_sm"]
    )

    assert result.exit_code == 0

    # Verify that the framework_callback was called with the correct value
    mock_framework_callback.assert_called_with("spacy")

    # Verify that Console.print was called to display the training information
    assert mock_print.called


@patch("rich.console.Console.print")
@patch("argilla.cli.training.__main__.framework_callback")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_training_with_options(mock_framework_callback, mock_print, runner):
    """Test training command with additional options."""
    # Set up the mock to return a valid framework
    mock_framework_callback.return_value = Framework.TRANSFORMERS

    result = runner.invoke(
        app,
        [
            "training",
            "--name",
            "test_dataset",
            "--framework",
            "transformers",
            "--model",
            "bert-base-uncased",
            "--workspace",
            "research",
            "--train-size",
            "0.8",
            "--seed",
            "42",
            "--device",
            "0",
            "--output-dir",
            "models/test_model",
        ],
    )

    assert result.exit_code == 0

    # Verify that the framework_callback was called with the correct value
    mock_framework_callback.assert_called_with("transformers")

    # Verify that Console.print was called to display the training information
    assert mock_print.called


@patch("rich.console.Console.print")
@patch("argilla.cli.training.__main__.framework_callback")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_training_with_query(mock_framework_callback, mock_print, runner):
    """Test training command with query parameter."""
    # Set up the mock to return a valid framework
    mock_framework_callback.return_value = Framework.SPACY

    result = runner.invoke(
        app,
        [
            "training",
            "--name",
            "test_dataset",
            "--framework",
            "spacy",
            "--model",
            "en_core_web_sm",
            "--query",
            "label:positive",
        ],
    )

    assert result.exit_code == 0

    # Verify that the framework_callback was called with the correct value
    mock_framework_callback.assert_called_with("spacy")

    # Verify that Console.print was called to display the training information
    assert mock_print.called


@patch("rich.console.Console.print")
@patch("argilla.cli.training.__main__.framework_callback")
@patch("json.loads")
@pytest.mark.skip(reason="Test temporarily disabled")
def test_training_with_config_update(mock_json_loads, mock_framework_callback, mock_print, runner):
    """Test training command with config update."""
    # Set up the mocks
    mock_framework_callback.return_value = Framework.SPACY
    mock_json_loads.return_value = {"max_steps": 1000, "learning_rate": 0.0001}

    result = runner.invoke(
        app,
        [
            "training",
            "--name",
            "test_dataset",
            "--framework",
            "spacy",
            "--model",
            "en_core_web_sm",
            "--update-config-kwargs",
            '{"max_steps": 1000, "learning_rate": 0.0001}',
        ],
    )

    assert result.exit_code == 0

    # Verify that the framework_callback was called with the correct value
    mock_framework_callback.assert_called_with("spacy")

    # Verify that json.loads was called to parse the config update
    mock_json_loads.assert_called_once_with('{"max_steps": 1000, "learning_rate": 0.0001}')

    # Verify that Console.print was called to display the training information
    assert mock_print.called
