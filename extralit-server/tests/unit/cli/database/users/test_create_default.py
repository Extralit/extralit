from typing import TYPE_CHECKING

from extralit_server.constants import DEFAULT_API_KEY, DEFAULT_PASSWORD, DEFAULT_USERNAME
from extralit_server.contexts import accounts
from extralit_server.models import User, UserRole
from tests.factories import WorkspaceSyncFactory

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from typer import Typer
    from typer.testing import CliRunner


def test_create_default(sync_db: "Session", cli_runner: "CliRunner", cli: "Typer"):
    result = cli_runner.invoke(cli, "database users create_default")

    assert result.exit_code == 0
    assert result.output != ""
    assert sync_db.query(User).count() == 1

    default_user = sync_db.query(User).filter_by(username=DEFAULT_USERNAME).first()
    assert default_user
    assert default_user.role == UserRole.owner
    assert default_user.api_key == DEFAULT_API_KEY
    assert accounts.verify_password(DEFAULT_PASSWORD, default_user.password_hash)
    assert [ws.name for ws in default_user.workspaces] == [DEFAULT_USERNAME]


def test_create_default_with_specific_api_key_and_password(sync_db: "Session", cli_runner: "CliRunner", cli: "Typer"):
    result = cli_runner.invoke(cli, "database users create_default --api-key my-api-key --password my-password")

    assert result.exit_code == 0
    assert result.output != ""
    assert sync_db.query(User).count() == 1

    default_user = sync_db.query(User).filter_by(username=DEFAULT_USERNAME).first()
    assert default_user
    assert default_user.role == UserRole.owner
    assert default_user.api_key == "my-api-key"
    assert accounts.verify_password("my-password", default_user.password_hash)
    assert [ws.name for ws in default_user.workspaces] == [DEFAULT_USERNAME]


def test_create_default_quiet(sync_db: "Session", cli_runner: "CliRunner", cli: "Typer"):
    result = cli_runner.invoke(cli, "database users create_default --quiet")

    assert result.exit_code == 0
    assert result.output == ""
    assert sync_db.query(User).count() == 1


def test_create_default_with_existent_default_user(sync_db: "Session", cli_runner: "CliRunner", cli: "Typer"):
    result = cli_runner.invoke(cli, "database users create_default")

    assert result.exit_code == 0
    assert result.output != ""
    assert sync_db.query(User).count() == 1

    result = cli_runner.invoke(cli, "database users create_default")

    assert result.exit_code == 0
    assert result.output == "User with default username already found on database, will not do anything.\n"
    assert sync_db.query(User).count() == 1


def test_create_default_with_existent_default_user_and_quiet(sync_db: "Session", cli_runner: "CliRunner", cli: "Typer"):
    result = cli_runner.invoke(cli, "database users create_default")

    assert result.exit_code == 0
    assert result.output != ""
    assert sync_db.query(User).count() == 1

    result = cli_runner.invoke(cli, "database users create_default --quiet")

    assert result.exit_code == 0
    assert result.output == ""
    assert sync_db.query(User).count() == 1


def test_create_default_with_existent_default_workspace(sync_db: "Session", cli_runner: "CliRunner", cli: "Typer"):
    WorkspaceSyncFactory.create(name=DEFAULT_USERNAME)

    result = cli_runner.invoke(cli, "database users create_default")

    assert result.exit_code == 0
    assert result.output != ""
    assert sync_db.query(User).count() == 1
