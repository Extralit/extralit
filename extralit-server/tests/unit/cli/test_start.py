from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock import MockerFixture
    from typer import Typer


def test_start_command(cli_runner: "CliRunner", cli: "Typer", mocker: "MockerFixture") -> None:
    uvicorn_run_mock = mocker.patch("uvicorn.run")
    result = cli_runner.invoke(cli, "start --host 1.1.1.1 --port 6899 --no-access-log")

    assert result.exit_code == 0
    uvicorn_run_mock.assert_called_once_with("extralit_server:app", host="1.1.1.1", port=6899, access_log=False)
