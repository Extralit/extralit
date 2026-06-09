from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def mock_session_local(mocker: "MockerFixture", async_db_proxy: "AsyncSession") -> None:
    mocker.patch("extralit_server.cli.database.users.create.AsyncSessionLocal", return_value=async_db_proxy)
    mocker.patch("extralit_server.cli.database.users.update.AsyncSessionLocal", return_value=async_db_proxy)
    mocker.patch("extralit_server.cli.database.users.create_default.AsyncSessionLocal", return_value=async_db_proxy)
    mocker.patch("extralit_server.cli.database.users.migrate.AsyncSessionLocal", return_value=async_db_proxy)
