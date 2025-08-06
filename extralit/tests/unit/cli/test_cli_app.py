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

from extralit.cli.app import app


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.mark.skip(reason="Test temporarily disabled")
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
