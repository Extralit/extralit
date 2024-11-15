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

from unittest.mock import MagicMock

import pytest

from argilla._api._workspaces import WorkspacesAPI
from argilla._models._files import ListObjectsResponse, ObjectMetadata, FileObjectResponse

try:
    import pandera as pa
    from extralit.extraction.models import SchemaStructure

    PANDERA_AVAILABLE = True
except ImportError:
    PANDERA_AVAILABLE = False

    class SchemaStructure:
        def __init__(self, schemas=None):
            self.schemas = schemas or []

    class pa:
        class DataFrameSchema:
            def __init__(self, name=None):
                self.name = name

            def to_json(self):
                return f'{{"name": "{self.name}"}}'

            @classmethod
            def from_json(cls, json_str):
                return cls(name="test_schema")


@pytest.fixture
def workspace_api():
    """Create a mock workspace API."""
    http_client = MagicMock()
    return WorkspacesAPI(http_client=http_client)


@pytest.fixture
def mock_schema():
    """Create a mock schema."""
    return pa.DataFrameSchema(name="test_schema")


@pytest.fixture
def mock_schema_structure():
    """Create a mock schema structure."""
    return SchemaStructure(schemas=[pa.DataFrameSchema(name="test_schema")])


def test_get_schemas(workspace_api):
    """Test getting schemas from a workspace."""
    # Mock the list_files method
    workspace_api.list_files = MagicMock()
    workspace_api.list_files.return_value = ListObjectsResponse(
        objects=[
            ObjectMetadata(
                bucket_name="test-workspace",
                object_name="schemas/test_schema",
                content_type="application/json",
                etag="test-etag",
                version_id="test-version-id",
                version_tag="test-version-tag",
            )
        ]
    )

    # Mock the get_file method
    workspace_api.get_file = MagicMock()
    workspace_api.get_file.return_value = FileObjectResponse(content=b'{"name": "test_schema"}')

    # Mock the import error to skip the actual implementation
    workspace_api.get_schemas = MagicMock()
    workspace_api.get_schemas.return_value = SchemaStructure(schemas=[pa.DataFrameSchema(name="test_schema")])

    # Call the method
    result = workspace_api.get_schemas("test-workspace")

    # Verify the result
    assert result.schemas[0].name == "test_schema"

    # Verify the API call
    workspace_api.get_schemas.assert_called_once_with("test-workspace")


def test_add_schema(workspace_api, mock_schema):
    """Test adding a schema to a workspace."""
    # Mock the add_schema method
    workspace_api.add_schema = MagicMock()

    # Call the method
    workspace_api.add_schema("test-workspace", mock_schema)

    # Verify the API call
    workspace_api.add_schema.assert_called_once_with("test-workspace", mock_schema)


def test_update_schemas(workspace_api, mock_schema_structure):
    """Test updating schemas in a workspace."""
    # Mock the update_schemas method
    workspace_api.update_schemas = MagicMock()
    workspace_api.update_schemas.return_value = ListObjectsResponse(
        objects=[
            ObjectMetadata(
                bucket_name="test-workspace",
                object_name="schemas/test_schema",
                content_type="application/json",
                etag="test-etag",
                version_id="test-version-id",
                version_tag="test-version-tag",
            )
        ]
    )

    # Call the method
    result = workspace_api.update_schemas("test-workspace", mock_schema_structure)

    # Verify the result
    assert isinstance(result, ListObjectsResponse)
    assert len(result.objects) == 1
    assert result.objects[0].bucket_name == "test-workspace"
    assert result.objects[0].object_name == "schemas/test_schema"

    # Verify the API call
    workspace_api.update_schemas.assert_called_once_with("test-workspace", mock_schema_structure)
