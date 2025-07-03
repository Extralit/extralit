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

import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass

from argilla_server.contexts.schemas import SchemaService
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
        with patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", False):
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

    async def test_sync_s3_schema_to_metadata_success(self):
        """Test successful sync of a specific schema from S3 to metadata."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        # Mock schema data
        schema_data = {
            "checks": [{"name": "singleton", "statistics": {"enabled": True}}],
            "columns": {"test_column": {"pandas_dtype": "object"}},
        }

        # Mock file response - using MagicMock instead of dataclass to avoid mutable default issues
        mock_response = MagicMock()
        mock_response.data = json.dumps(schema_data).encode("utf-8")

        mock_metadata = MagicMock()
        mock_metadata.version_id = "test_version_123"

        mock_file_response = MagicMock()
        mock_file_response.response = mock_response
        mock_file_response.metadata = mock_metadata

        # Mock the async session
        mock_db = AsyncMock()

        with (
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
            patch("argilla_server.contexts.files.get_object") as mock_get_object,
            patch("argilla_server.contexts.schemas.from_json") as mock_from_json,
        ):
            mock_get_object.return_value = mock_file_response
            mock_from_json.return_value = MagicMock()  # Mock pandera schema

            result = await service.sync_s3_schema_to_metadata(mock_db, workspace, "test_schema")

            # Verify the result
            assert "schemas" in result
            assert len(result["schemas"]) == 1
            assert result["schemas"][0]["name"] == "test_schema"
            assert result["schemas"][0]["is_singleton"] is True
            assert result["schemas"][0]["s3_path"] == "schemas/test_schema.json"
            assert result["schemas"][0]["version_id"] == "test_version_123"
            assert "last_sync" in result

            # Verify S3 call
            mock_get_object.assert_called_once_with(
                storage, workspace.name, "schemas/test_schema.json", include_versions=True
            )

    async def test_sync_s3_schema_to_metadata_without_pandera(self):
        """Test sync schema when pandera is not available."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)
        mock_db = AsyncMock()

        with patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", False):
            with pytest.raises(RuntimeError) as exc_info:
                await service.sync_s3_schema_to_metadata(mock_db, workspace, "test_schema")

            assert "Pandera is not available" in str(exc_info.value)

    async def test_sync_s3_schema_to_metadata_invalid_json(self):
        """Test sync schema with invalid JSON data."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)
        mock_db = AsyncMock()

        # Mock invalid JSON response
        mock_response = MagicMock()
        mock_response.data = b"invalid json"

        mock_file_response = MagicMock()
        mock_file_response.response = mock_response

        with (
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
            patch("argilla_server.contexts.files.get_object") as mock_get_object,
        ):
            mock_get_object.return_value = mock_file_response

            with pytest.raises(json.JSONDecodeError):
                await service.sync_s3_schema_to_metadata(mock_db, workspace, "test_schema")

    async def test_sync_s3_schema_to_metadata_update_existing(self):
        """Test sync schema that updates an existing schema in metadata."""
        workspace = await WorkspaceFactory.create(
            metadata_={
                "schema_configuration": {
                    "schemas": [
                        {
                            "name": "test_schema",
                            "is_singleton": False,
                            "s3_path": "schemas/test_schema.json",
                            "version_id": "old_version",
                            "dependencies": [],
                        }
                    ],
                    "last_sync": "2024-01-01T00:00:00Z",
                }
            }
        )
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)
        mock_db = AsyncMock()

        # Mock schema data without singleton check
        schema_data = {
            "checks": [],
            "columns": {"test_column": {"pandas_dtype": "object"}},
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(schema_data).encode("utf-8")

        mock_metadata = MagicMock()
        mock_metadata.version_id = "new_version_456"

        mock_file_response = MagicMock()
        mock_file_response.response = mock_response
        mock_file_response.metadata = mock_metadata

        with (
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
            patch("argilla_server.contexts.files.get_object") as mock_get_object,
            patch("argilla_server.contexts.schemas.from_json") as mock_from_json,
        ):
            mock_get_object.return_value = mock_file_response
            mock_from_json.return_value = MagicMock()

            result = await service.sync_s3_schema_to_metadata(mock_db, workspace, "test_schema")

            # Verify the existing schema was updated
            assert len(result["schemas"]) == 1
            assert result["schemas"][0]["name"] == "test_schema"
            assert result["schemas"][0]["is_singleton"] is False  # No singleton check in schema
            assert result["schemas"][0]["version_id"] == "new_version_456"

    async def test_sync_all_s3_schemas_to_metadata_success(self):
        """Test successful sync of all schemas from S3 to metadata."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)
        mock_db = AsyncMock()

        # Mock object list response
        @dataclass
        class MockObject:
            object_name: str

        objects_response = MagicMock()
        objects_response.objects = [
            MockObject("schemas/schema1.json"),
            MockObject("schemas/schema2.json"),
            MockObject("schemas/not_schema.txt"),  # Should be ignored
        ]

        # Mock schema data
        schema1_data = {
            "checks": [{"name": "singleton", "statistics": {"enabled": True}}],
            "columns": {"test_column": {"pandas_dtype": "object"}},
        }
        schema2_data = {
            "checks": [],
            "columns": {"test_column": {"pandas_dtype": "object"}},
        }

        # Mock file responses using MagicMock
        mock_response1 = MagicMock()
        mock_response1.data = json.dumps(schema1_data).encode("utf-8")
        mock_metadata1 = MagicMock()
        mock_metadata1.version_id = "version_123"
        mock_file_response1 = MagicMock()
        mock_file_response1.response = mock_response1
        mock_file_response1.metadata = mock_metadata1

        mock_response2 = MagicMock()
        mock_response2.data = json.dumps(schema2_data).encode("utf-8")
        mock_metadata2 = MagicMock()
        mock_metadata2.version_id = "version_123"
        mock_file_response2 = MagicMock()
        mock_file_response2.response = mock_response2
        mock_file_response2.metadata = mock_metadata2

        with (
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
            patch("argilla_server.contexts.files.list_objects") as mock_list_objects,
            patch("argilla_server.contexts.files.get_object") as mock_get_object,
        ):
            mock_list_objects.return_value = objects_response
            # Return different responses for different files
            mock_get_object.side_effect = [mock_file_response1, mock_file_response2]

            result = await service.sync_all_s3_schemas_to_metadata(mock_db, workspace, "schemas/")

            # Verify the result
            assert "schemas" in result
            assert len(result["schemas"]) == 2

            # Check schema1 (singleton)
            schema1 = next(s for s in result["schemas"] if s["name"] == "schema1")
            assert schema1["is_singleton"] is True
            assert schema1["s3_path"] == "schemas/schema1.json"

            # Check schema2 (not singleton)
            schema2 = next(s for s in result["schemas"] if s["name"] == "schema2")
            assert schema2["is_singleton"] is False
            assert schema2["s3_path"] == "schemas/schema2.json"

            assert "last_sync" in result

            # Verify S3 calls
            mock_list_objects.assert_called_once_with(
                storage, workspace.name, prefix="schemas/", include_version=False, recursive=True
            )
            assert mock_get_object.call_count == 2

    async def test_sync_all_s3_schemas_to_metadata_without_pandera(self):
        """Test sync all schemas when pandera is not available."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)
        mock_db = AsyncMock()

        with patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", False):
            with pytest.raises(RuntimeError) as exc_info:
                await service.sync_all_s3_schemas_to_metadata(mock_db, workspace, "schemas/")

            assert "Pandera is not available" in str(exc_info.value)

    async def test_sync_all_s3_schemas_to_metadata_skip_invalid_schema(self):
        """Test sync all schemas skips invalid schemas and continues with valid ones."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)
        mock_db = AsyncMock()

        # Mock object list response
        @dataclass
        class MockObject:
            object_name: str

        objects_response = MagicMock()
        objects_response.objects = [
            MockObject("schemas/valid_schema.json"),
            MockObject("schemas/invalid_schema.json"),
        ]

        # Mock schema data
        valid_schema_data = {
            "checks": [],
            "columns": {"test_column": {"pandas_dtype": "object"}},
        }

        # Mock file responses using MagicMock
        mock_valid_response = MagicMock()
        mock_valid_response.data = json.dumps(valid_schema_data).encode("utf-8")
        mock_valid_metadata = MagicMock()
        mock_valid_metadata.version_id = "version_123"
        mock_valid_file_response = MagicMock()
        mock_valid_file_response.response = mock_valid_response
        mock_valid_file_response.metadata = mock_valid_metadata

        mock_invalid_response = MagicMock()
        mock_invalid_response.data = b"invalid json"
        mock_invalid_metadata = MagicMock()
        mock_invalid_metadata.version_id = "version_123"
        mock_invalid_file_response = MagicMock()
        mock_invalid_file_response.response = mock_invalid_response
        mock_invalid_file_response.metadata = mock_invalid_metadata

        with (
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
            patch("argilla_server.contexts.files.list_objects") as mock_list_objects,
            patch("argilla_server.contexts.files.get_object") as mock_get_object,
        ):
            mock_list_objects.return_value = objects_response
            mock_get_object.side_effect = [mock_valid_file_response, mock_invalid_file_response]

            result = await service.sync_all_s3_schemas_to_metadata(mock_db, workspace, "schemas/")

            # Should only have the valid schema
            assert "schemas" in result
            assert len(result["schemas"]) == 1
            assert result["schemas"][0]["name"] == "valid_schema"

    async def test_create_schema_structure_from_metadata_success(self):
        """Test successful creation of SchemaStructure from workspace metadata."""
        workspace = await WorkspaceFactory.create(
            metadata_={
                "schema_configuration": {
                    "schemas": [
                        {
                            "name": "publication",
                            "is_singleton": True,
                            "s3_path": "schemas/publication.json",
                            "version_id": "pub_version",
                            "dependencies": [],
                        },
                        {
                            "name": "method",
                            "is_singleton": False,
                            "s3_path": "schemas/method.json",
                            "version_id": "method_version",
                            "dependencies": [],
                        },
                    ],
                    "last_sync": "2024-01-01T00:00:00Z",
                }
            }
        )
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        # Mock schema data
        pub_schema_data = {"columns": {"title": {"pandas_dtype": "object"}}}
        method_schema_data = {"columns": {"name": {"pandas_dtype": "object"}}}

        # Mock file responses using MagicMock
        mock_pub_response = MagicMock()
        mock_pub_response.data = json.dumps(pub_schema_data).encode("utf-8")
        mock_pub_file_response = MagicMock()
        mock_pub_file_response.response = mock_pub_response

        mock_method_response = MagicMock()
        mock_method_response.data = json.dumps(method_schema_data).encode("utf-8")
        mock_method_file_response = MagicMock()
        mock_method_file_response.response = mock_method_response

        # Mock SchemaStructure class
        mock_schema_structure = MagicMock()
        mock_pub_schema = MagicMock()
        mock_method_schema = MagicMock()

        with (
            patch("argilla_server.contexts.schemas.EXTRALIT_AVAILABLE", True),
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
            patch("argilla_server.contexts.schemas.SchemaStructure") as mock_schema_structure_class,
            patch("argilla_server.contexts.files.get_object") as mock_get_object,
            patch("argilla_server.contexts.schemas.from_json") as mock_from_json,
        ):
            mock_get_object.side_effect = [mock_pub_file_response, mock_method_file_response]
            mock_from_json.side_effect = [mock_pub_schema, mock_method_schema]
            mock_schema_structure_class.return_value = mock_schema_structure

            result = await service.create_schema_structure_from_metadata(workspace)

            # Verify SchemaStructure was created with correct parameters
            assert result == mock_schema_structure
            mock_schema_structure_class.assert_called_once_with(
                schemas=[mock_pub_schema, mock_method_schema], singleton_schema=mock_pub_schema
            )

            # Verify S3 calls were made with correct parameters
            assert mock_get_object.call_count == 2
            mock_get_object.assert_any_call(
                storage, workspace.name, "schemas/publication.json", version_id="pub_version"
            )
            mock_get_object.assert_any_call(storage, workspace.name, "schemas/method.json", version_id="method_version")

    async def test_create_schema_structure_from_metadata_without_extralit(self):
        """Test creating SchemaStructure when extralit is not available."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        with patch("argilla_server.contexts.schemas.EXTRALIT_AVAILABLE", False):
            result = await service.create_schema_structure_from_metadata(workspace)
            assert result is None

    async def test_create_schema_structure_from_metadata_without_pandera(self):
        """Test creating SchemaStructure when pandera is not available."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        with (
            patch("argilla_server.contexts.schemas.EXTRALIT_AVAILABLE", True),
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", False),
        ):
            result = await service.create_schema_structure_from_metadata(workspace)
            assert result is None

    async def test_create_schema_structure_from_metadata_empty_config(self):
        """Test creating SchemaStructure with empty schema configuration."""
        workspace = await WorkspaceFactory.create()
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        mock_schema_structure = MagicMock()

        with (
            patch("argilla_server.contexts.schemas.EXTRALIT_AVAILABLE", True),
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
            patch("argilla_server.contexts.schemas.SchemaStructure") as mock_schema_structure_class,
        ):
            mock_schema_structure_class.return_value = mock_schema_structure

            result = await service.create_schema_structure_from_metadata(workspace)

            # Should create empty SchemaStructure
            assert result == mock_schema_structure
            mock_schema_structure_class.assert_called_once_with(schemas=[])

    async def test_create_schema_structure_from_metadata_with_cache(self):
        """Test creating SchemaStructure uses cache when available."""
        workspace = await WorkspaceFactory.create(
            metadata_={
                "schema_configuration": {
                    "schemas": [
                        {
                            "name": "test_schema",
                            "is_singleton": False,
                            "s3_path": "schemas/test_schema.json",
                            "version_id": "version_123",
                            "dependencies": [],
                        }
                    ],
                    "last_sync": "2024-01-01T00:00:00Z",
                }
            }
        )
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        # Add to cache
        cache_key = f"workspace_{workspace.id}_schemas"
        cached_structure = MagicMock()
        service._schema_cache[cache_key] = cached_structure

        with (
            patch("argilla_server.contexts.schemas.EXTRALIT_AVAILABLE", True),
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
        ):
            result = await service.create_schema_structure_from_metadata(workspace)

            # Should return cached result without S3 calls
            assert result == cached_structure

    async def test_create_schema_structure_from_metadata_skip_failed_schema(self):
        """Test creating SchemaStructure skips schemas that fail to load."""
        workspace = await WorkspaceFactory.create(
            metadata_={
                "schema_configuration": {
                    "schemas": [
                        {
                            "name": "valid_schema",
                            "is_singleton": False,
                            "s3_path": "schemas/valid_schema.json",
                            "version_id": "version_123",
                            "dependencies": [],
                        },
                        {
                            "name": "invalid_schema",
                            "is_singleton": False,
                            "s3_path": "schemas/invalid_schema.json",
                            "version_id": "version_456",
                            "dependencies": [],
                        },
                    ],
                    "last_sync": "2024-01-01T00:00:00Z",
                }
            }
        )
        storage = LocalFileStorage(tempfile.mkdtemp())
        service = SchemaService(storage)

        # Mock schema data
        valid_schema_data = {"columns": {"name": {"pandas_dtype": "object"}}}

        # Mock file response using MagicMock
        mock_valid_response = MagicMock()
        mock_valid_response.data = json.dumps(valid_schema_data).encode("utf-8")
        mock_valid_file_response = MagicMock()
        mock_valid_file_response.response = mock_valid_response

        mock_schema_structure = MagicMock()
        mock_valid_schema = MagicMock()

        with (
            patch("argilla_server.contexts.schemas.EXTRALIT_AVAILABLE", True),
            patch("argilla_server.contexts.schemas.PANDERA_AVAILABLE", True),
            patch("argilla_server.contexts.schemas.SchemaStructure") as mock_schema_structure_class,
            patch("argilla_server.contexts.files.get_object") as mock_get_object,
            patch("argilla_server.contexts.schemas.from_json") as mock_from_json,
        ):
            # First call succeeds, second call fails
            mock_get_object.side_effect = [mock_valid_file_response, Exception("File not found")]
            mock_from_json.return_value = mock_valid_schema
            mock_schema_structure_class.return_value = mock_schema_structure

            result = await service.create_schema_structure_from_metadata(workspace)

            # Should create SchemaStructure with only the valid schema
            assert result == mock_schema_structure
            mock_schema_structure_class.assert_called_once_with(schemas=[mock_valid_schema], singleton_schema=None)

            # Verify both S3 calls were attempted
            assert mock_get_object.call_count == 2
