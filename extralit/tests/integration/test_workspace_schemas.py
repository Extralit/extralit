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

import uuid

import pytest

try:
    import pandera as pa

    from extralit._models._schema import SchemaStructure

    PANDERA_AVAILABLE = True
except ImportError:
    PANDERA_AVAILABLE = False
    pytest.skip("pandera and extralit are required for schema tests", allow_module_level=True)

from extralit import Workspace


@pytest.fixture
def test_schema():
    """Create a test schema."""
    schema = pa.DataFrameSchema(
        name=f"test_schema_{uuid.uuid4().hex[:8]}",
        columns={
            "text": pa.Column(pa.String),
            "label": pa.Column(pa.String),
            "score": pa.Column(pa.Float, nullable=True),
        },
    )
    return schema


@pytest.fixture
def test_schema_structure(test_schema):
    """Create a test schema structure."""
    return SchemaStructure(schemas=[test_schema])


class TestWorkspaceSchemas:
    def test_get_schemas(self, workspace: Workspace):
        """Test getting schemas from a workspace."""
        # Get schemas from the workspace
        schemas = workspace.list_schemas()

        # Verify the result
        assert hasattr(schemas, "schemas")
        # Initially, there should be no schemas
        assert len(schemas.schemas) == 0

    def test_add_and_get_schema(self, workspace: Workspace, test_schema):
        """Test adding a schema to a workspace and getting it."""

    def test_update_schemas(self, workspace: Workspace, test_schema_structure):
        """Test updating schemas in a workspace."""

    def test_add_schema_with_exclude(self, workspace: Workspace, test_schema):
        """Test getting schemas with exclude parameter."""
        # Add the schema
        workspace.add_schema(test_schema)

        # Get schemas from the workspace with exclude
        schemas = workspace.list_schemas(exclude=[test_schema.name])

        # Verify the schema is not in the list
        assert not any(schema.name == test_schema.name for schema in schemas.schemas)

    def test_schema_to_json_and_back(self, workspace: Workspace, test_schema):
        pass
