from pathlib import Path
from typing import TYPE_CHECKING
from argilla.client.sdk.v1.files.models import ListObjectsResponse, ObjectMetadata
import pytest
from datetime import datetime

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock import MockerFixture
    from typer import Typer

@pytest.mark.asyncio
@pytest.mark.usefixtures("login_mock")
async def test_list_schemas(
    cli_runner: "CliRunner", cli: "Typer", mocker: "MockerFixture"
) -> None:
    # Mock the Workspace.from_name method
    workspace_from_name_mock = mocker.patch("argilla.client.workspaces.Workspace.from_name")
    
    # Create a mock return value for list_files
    mock_file_objects = [
        ObjectMetadata(
            bucket_name="unit-test",
            object_name="schema1.json",
            version_id="v1",
            version_tag="tag1",
            last_modified=datetime.now(),
            metadata={"key": "value"},
            etag="etag1"
        ),
        ObjectMetadata(
            bucket_name="unit-test",
            object_name="schema2.json",
            version_id="v2",
            version_tag="tag2",
            last_modified=datetime.now(),
            metadata={"key": "value"},
            etag="etag2"
        )
    ]
    list_files_mock = mocker.patch(
        "argilla.client.workspaces.Workspace.list_files",
        return_value=ListObjectsResponse(objects=mock_file_objects)
    )

    # Invoke the CLI command
    result = cli_runner.invoke(cli, ["schemas", "--workspace", "unit-test", "list", "--versions"])

    # Assertions
    assert result.exit_code == 0
    workspace_from_name_mock.assert_called_once_with("unit-test")
    # list_files_mock.assert_called_once_with(ANY, include_version=True)