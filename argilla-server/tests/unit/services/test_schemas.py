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

import pytest
import tempfile
from unittest.mock import patch

from argilla_server.services.schemas import SchemaService
from argilla_server.contexts.files import LocalFileStorage

from tests.factories import WorkspaceFactory


@pytest.mark.asyncio
class TestSchemaService:
    async def test_init_schema_service(self):
        """Test that SchemaService can be initialized."""
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)
        assert service is not None
        assert service.minio_client is not None

    async def test_get_workspace_schema_configuration_empty(self):
        """Test getting schema configuration from workspace with no metadata."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        config = await service.get_workspace_schema_configuration(workspace)

        assert config == {"schema_configuration": {"schemas": [], "last_sync": None}}

    async def test_get_workspace_schema_configuration_with_metadata(self):
        """Test getting schema configuration from workspace with metadata."""
        workspace = await WorkspaceFactory.create(
            metadata_={
                "schema_configuration": {
                    "schemas": [
                        {
                            "name": "test_schema",
                            "is_singleton": True,
                            "s3_path": "schemas/test_schema.json",
                            "version_id": "abc123",
                            "dependencies": [],
                        }
                    ],
                    "last_sync": "2024-01-01T00:00:00Z",
                }
            }
        )
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        config = await service.get_workspace_schema_configuration(workspace)

        assert config["schema_configuration"]["schemas"][0]["name"] == "test_schema"
        assert config["schema_configuration"]["schemas"][0]["is_singleton"] is True
        assert config["schema_configuration"]["last_sync"] == "2024-01-01T00:00:00Z"

    async def test_validate_schema_without_pandera(self):
        """Test schema validation when pandera is not available."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        # Mock PANDERA_AVAILABLE to False
        with patch("argilla_server.services.schemas.PANDERA_AVAILABLE", False):
            is_valid, error = await service.validate_schema(workspace, "test_schema")

            assert is_valid is False
            assert "Pandera is not available" in error

    async def test_clear_cache(self):
        """Test clearing the schema cache."""
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        # Add something to cache
        service._schema_cache["test_key"] = "test_value"
        assert len(service._schema_cache) == 1

        # Clear cache
        service.clear_cache()
        assert len(service._schema_cache) == 0

    async def test_clear_cache_specific_workspace(self):
        """Test clearing cache for a specific workspace."""
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        workspace = await WorkspaceFactory.create()
        cache_key = f"workspace_{workspace.id}_schemas"
        other_key = "other_workspace_schemas"

        # Add items to cache
        service._schema_cache[cache_key] = "test_value"
        service._schema_cache[other_key] = "other_value"
        assert len(service._schema_cache) == 2

        # Clear cache for specific workspace
        service.clear_cache(workspace.id)

        assert cache_key not in service._schema_cache
        assert other_key in service._schema_cache
        assert len(service._schema_cache) == 1
