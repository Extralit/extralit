import contextlib
import os
from pathlib import Path
import sys
from typing import Any, Generator, Optional
import openai
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from pytest_mock import MockerFixture

from ..database import SyncTestSession, TestSession, set_task

@pytest.fixture(scope="function")
def client(request, mocker: "MockerFixture") -> Generator[TestClient, None, None]:
    from extralit.server.app import app

    async def override_get_async_db():
        session = TestSession()
        yield session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_dependencies(mocker: "MockerFixture"):
    mocker.patch("extralit.server.context.vectordb.get_weaviate_client", return_value=MagicMock())
    mocker.patch("extralit.server.context.files.get_minio_client", return_value=MagicMock())
    mocker.patch("extralit.server.context.llamaindex.get_langfuse_callback", return_value=MagicMock()) 



