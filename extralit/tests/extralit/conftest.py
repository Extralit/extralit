# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Generator
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from pytest_mock import MockerFixture

import pandas as pd
import pandera as pa
from pandera.typing import Index, Series

from extralit.schema.checks import register_check_methods
from extralit.extraction.models.schema import SchemaStructure
from extralit.storage.files import FileHandler, StorageType

register_check_methods()

from ..database import TestSession


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


@pytest.fixture
def mock_paper() -> pd.Series:
    return pd.Series({"file_path": "/tmp/test_pdf.pdf"}, name="test-paper")


@pytest.fixture
def local_file_handler() -> FileHandler:
    return MagicMock(spec=FileHandler)


@pytest.fixture
def s3_file_handler() -> FileHandler:
    # Create a mock FileHandler with S3 storage type
    file_handler = FileHandler(
        base_path="data/preprocessing/", storage_type=StorageType.S3, bucket_name="test-workspace"
    )
    file_handler.client = MagicMock()

    return file_handler
