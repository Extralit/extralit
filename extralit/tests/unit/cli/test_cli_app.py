# Copyright 2024-present, Argilla, Inc.
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

from argilla.cli.app import app


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


def test_app_help(runner):
    """Test that the CLI app shows help message."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Extralit CLI" in result.stdout


def test_command_modules_registered(runner):
    """Test that all command modules are properly registered."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    
    # Check that all command modules are listed in the help output
    expected_commands = [
        "datasets",
        "extraction",
        "info",
        "login",
        "logout",
        "schemas",
        "training",
        "users",
        "whoami",
        "workspaces",
    ]
    
    for command in expected_commands:
        assert command in result.stdout, f"Command '{command}' not found in CLI help output"


@pytest.mark.parametrize(
    "command", 
    ["datasets", "extraction", "info", "login", "logout", "schemas", "training", "users", "whoami", "workspaces"]
)
def test_subcommand_help(runner, command):
    """Test that each subcommand shows help message."""
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0, f"Error in {command} command help: {result.stdout}"