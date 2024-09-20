from typing import Any, Generator, Optional
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from pytest_mock import MockerFixture

import pandera as pa
from pandera.typing import Index, Series
from extralit.schema.checks import register_check_methods
from extralit.extraction.models.schema import SchemaStructure

register_check_methods()

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


class MockSchema(pa.DataFrameModel):
    """
    General information about the publication, extracted once per paper.
    """
    reference: Index[str] = pa.Field(check_name=True)
    title: Series[str] = pa.Field()
    authors: Series[str] = pa.Field()
    journal: Series[str] = pa.Field()
    publication_year: Series[int] = pa.Field(ge=1900, le=2100)
    doi: Series[str] = pa.Field(nullable=True)
    
    class Config:
        singleton = True


@pytest.fixture
def singleton_schema() -> pa.DataFrameModel:
    return MockSchema


@pytest.fixture
def schema_structure(singleton_schema: pa.DataFrameModel) -> SchemaStructure:
    return SchemaStructure(schemas=[singleton_schema])