import os
from typing import TYPE_CHECKING, Optional
import openai
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from extralit.extraction.models.schema import SchemaStructure

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from pytest_mock import MockerFixture

from tests.extralit.helpers import mock_chat_completion_stream_v1

class CachedOpenAIApiKeys:
    """
    Saves the users' OpenAI API key and OpenAI API type either in
    the environment variable or set to the library itself.
    This allows us to run tests by setting it without plowing over
    the local environment.
    """

    def __init__(
        self,
        set_env_key_to: Optional[str] = "",
        set_library_key_to: Optional[str] = None,
        set_fake_key: bool = False,
        set_env_type_to: Optional[str] = "",
        set_library_type_to: str = "open_ai",  # default value in openai package
    ):
        self.set_env_key_to = set_env_key_to
        self.set_library_key_to = set_library_key_to
        self.set_fake_key = set_fake_key
        self.set_env_type_to = set_env_type_to
        self.set_library_type_to = set_library_type_to

    def __enter__(self) -> None:
        self.api_env_variable_was = os.environ.get("OPENAI_API_KEY", "")
        self.api_env_type_was = os.environ.get("OPENAI_API_TYPE", "")
        self.openai_api_key_was = openai.api_key
        self.openai_api_type_was = openai.api_type

        os.environ["OPENAI_API_KEY"] = str(self.set_env_key_to)
        os.environ["OPENAI_API_TYPE"] = str(self.set_env_type_to)

        if self.set_fake_key:
            os.environ["OPENAI_API_KEY"] = "sk-" + "a" * 48

    # No matter what, set the environment variable back to what it was
    def __exit__(self, *exc: object) -> None:
        os.environ["OPENAI_API_KEY"] = str(self.api_env_variable_was)
        os.environ["OPENAI_API_TYPE"] = str(self.api_env_type_was)
        openai.api_key = self.openai_api_key_was
        openai.api_type = self.openai_api_type_was


def test_health_check(client: "TestClient"):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_schemas(client: "TestClient", mocker: "MockerFixture"):
    mock_schema_structure = mocker.patch("extralit.server.app.SchemaStructure.from_s3")
    mock_schema_structure.return_value.ordering = {"schema": "value"}

    response = client.get("/schemas/test-workspace")
    assert response.status_code == 200
    assert response.json() == {"schema": "value"}


@patch("llama_index.llms.openai.base.SyncOpenAI")
def test_chat(
    MockSyncOpenAI: MagicMock, client: "TestClient", mocker: "MockerFixture",
):
    with CachedOpenAIApiKeys(set_fake_key=True):
        mock_instance = MockSyncOpenAI.return_value
        mock_instance.chat.completions.create.return_value = (
            mock_chat_completion_stream_v1(responses=["res", "ponse"])
        )

        mock_vectordb_contains_any = mocker.patch("extralit.server.app.vectordb_contains_any")
        mock_vectordb_contains_any.return_value = True

        response = client.get("/chat", params={
            "query": "test query",
            "workspace": "test-workspace",
            "reference": "test-reference",
            "k": 5,
            "chat_mode": "best",
            "llm_model": "gpt-3.5-turbo",
            "args": [None],
            "kwargs": {}
        })
        
        assert response.status_code == 200
        assert response.content == b"response"

        MockSyncOpenAI.assert_called_once()


def test_extraction(
    client: "TestClient", 
    mocker: "MockerFixture", 
    schema_structure: "SchemaStructure"
):
    with CachedOpenAIApiKeys(set_fake_key=True):
        # mock_load_index = mocker.patch("extralit.server.app.load_index")
        
        mock_extract_schema = mocker.patch("extralit.server.app.extract_schema")
        mock_extract_schema.return_value = (pd.DataFrame({"col": ["value"]}), MagicMock())
        
        mock_schema_structure = mocker.patch("extralit.server.app.SchemaStructure.from_s3")
        mock_schema_structure.return_value = schema_structure

        response = client.post(
            "/extraction", 
            json={
                "reference": "test-reference",
                "schema_name": "MockSchema",
                "extractions": {
                    "MockSchema": [{"key": "value"}]
                },
                "columns": ["col"],
                "headers": ["header"],
                "types": None,
                "prompt": "test prompt",
            }, 
            params={
                "workspace": "test-workspace",
                "args": [None],
                "kwargs": {}
            }
        )
        
        assert response.status_code == 201
        assert response.json() == {
            "data": [{"col": "value", "index": 0}],
            'schema': {
                'fields': [
                    {'extDtype': None, 'name': 'index', 'type': 'integer'},
                    {'extDtype': None, 'name': 'col','type': 'string'}
                ],
                'pandas_version': '1.4.0',
                'primaryKey': ['index']
            },
        }


def test_segments(client: "TestClient", mocker: "MockerFixture"):
    mock_get_nodes_metadata = mocker.patch("extralit.server.app.get_nodes_metadata")
    mock_get_nodes_metadata.return_value = [{
        "doc_id": "test-doc-id",
        "header": "test-header",
        "page_number": 1,
        "key": "value",
    }]

    response = client.get("/segments/", params={
        "workspace": "test-workspace",
        "reference": "test-reference",
        "types": ["text"],
        "limit": 100
    })
    assert response.status_code == 200
    assert response.json() == {'items': [
        {'doc_id': 'test-doc-id', 'header': 'test-header', 'page_number': 1, 'type': None}
        ]
    }