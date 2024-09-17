from typing import TYPE_CHECKING
from unittest.mock import ANY, call

import pytest
from rich.table import Table
from extralit.extraction.models.schema import SchemaStructure
from argilla.client.workspaces import Workspace

from tests.factories import WorkspaceFactory

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock import MockerFixture
    from typer import Typer


@pytest.mark.asyncio
@pytest.mark.usefixtures("login_mock")
class TestSuiteSchemaCommands:
    async def test_list_schemas(
        self, cli_runner: "CliRunner", cli: "Typer", mocker: "MockerFixture"
    ) -> None:
        workspace = await WorkspaceFactory(name="unit-test")
        list_files_mock = mocker.patch("argilla.client.workspaces.Workspace.list_files")

        result = cli_runner.invoke(cli, f"schemas --workspace {workspace.name} list --versions")

        assert result.exit_code == 0
        list_files_mock.assert_called_once_with(ANY, include_version=True)
