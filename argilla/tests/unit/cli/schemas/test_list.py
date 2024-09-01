from typing import TYPE_CHECKING
from unittest.mock import ANY, call

import pytest
from rich.table import Table
from extralit.extraction.models.schema import SchemaStructure
from argilla.client.workspaces import Workspace

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock import MockerFixture
    from typer import Typer


@pytest.mark.usefixtures("login_mock")
class TestSuiteSchemaCommands:
    def test_list_schemas(
        self, cli_runner: "CliRunner", cli: "Typer", mocker: "MockerFixture"
    ) -> None:
        workspace_from_name_mock = mocker.patch("argilla.client.workspaces.Workspace.from_name")
        list_files_mock = mocker.patch("argilla.client.workspaces.Workspace.list_files")

        result = cli_runner.invoke(cli, "schemas --workspace unit-test list --versions")

        assert result.exit_code == 0
        # list_files_mock.assert_called_once_with(ANY, include_version=True)
        workspace_from_name_mock.assert_called_once_with("unit-test")
