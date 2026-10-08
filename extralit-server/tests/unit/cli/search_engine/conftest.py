import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def mock_session_local(mocker: MockerFixture, async_db_proxy: AsyncSession) -> None:
    mocker.patch("extralit_server.cli.search_engine.reindex.AsyncSessionLocal", return_value=async_db_proxy)
