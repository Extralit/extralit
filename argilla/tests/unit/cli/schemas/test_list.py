from typing import TYPE_CHECKING

from argilla.client.sdk.v1.files.models import ListObjectsResponse
import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock import MockerFixture
    from typer import Typer


@pytest.mark.asyncio
@pytest.mark.usefixtures("login_mock")
async def test_list_schemas(
    cli_runner: "CliRunner", cli: "Typer", mocker: "MockerFixture"
) -> None:
    workspace_from_name_mock = mocker.patch("argilla.client.workspaces.Workspace.from_name")
    list_files_mock = mocker.patch("argilla.client.workspaces.Workspace.list_files", return_value=ListObjectsResponse())

    result = cli_runner.invoke(cli, "schemas --workspace unit-test list --versions")

    assert result.exit_code == 0
    workspace_from_name_mock.assert_called_once_with("unit-test")
