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
