import pytest
from typer import Typer
from typer.testing import CliRunner

from extralit_server.cli import app


@pytest.fixture(scope="session")
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(scope="session")
def cli() -> Typer:
    return app
