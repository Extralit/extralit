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
import logging
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional, Union, Tuple
from uuid import UUID

from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from argilla_server.contexts import files
from argilla_server.models import Workspace

try:
    import pandera as pa
    from pandera.io.pandas_io import from_json, from_yaml

    PANDERA_AVAILABLE = True
except ImportError:
    PANDERA_AVAILABLE = False
    pa = None
    from_json = None
    from_yaml = None

try:
    from extralit.extraction.models.schema import SchemaStructure
    from extralit.constants import DEFAULT_SCHEMA_S3_PATH

    EXTRALIT_AVAILABLE = True
except ImportError:
    # Handle case where extralit package is not available
    SchemaStructure = None
    DEFAULT_SCHEMA_S3_PATH = "schemas/"
    EXTRALIT_AVAILABLE = False

_LOGGER = logging.getLogger(__name__)


class SchemaService:
    """
    Service for managing workspace-level schema configuration.

    This service provides functionality to:
    - Sync S3 schema files with workspace metadata configuration
    - Create SchemaStructure objects from workspace metadata
    - Validate schemas using Pandera DataFrameSchema
    - Add/remove schemas while maintaining S3 file versioning
    - Cache schema configurations for improved performance
    """

    def __init__(self, minio_client: Union[Minio, files.LocalFileStorage]):
        self.minio_client = minio_client
        self._schema_cache: Dict[str, Any] = {}

    async def get_workspace_schema_configuration(self, workspace: Workspace) -> Dict[str, Any]:
        """
        Get the schema configuration for a workspace.

        Args:
            workspace: The workspace to get schema configuration for

        Returns:
            Dict containing the schema configuration, or empty dict if none exists
        """
        if not workspace.metadata_:
            return {"schema_configuration": {"schemas": [], "last_sync": None}}

        schema_config = workspace.metadata_.get("schema_configuration", {"schemas": [], "last_sync": None})
        return {"schema_configuration": schema_config}

    async def update_workspace_schema_configuration(
        self, db: AsyncSession, workspace: Workspace, schema_config: Dict[str, Any]
    ) -> Workspace:
        """
        Update the schema configuration for a workspace.

        Args:
            db: Database session
            workspace: The workspace to update
            schema_config: The new schema configuration

        Returns:
            Updated workspace
        """
        if not workspace.metadata_:
            workspace.metadata_ = {}

        workspace.metadata_["schema_configuration"] = schema_config
        workspace.metadata_["schema_configuration"]["last_sync"] = datetime.utcnow().isoformat()

        await db.commit()
        await db.refresh(workspace)

        # Clear cache for this workspace
        cache_key = f"workspace_{workspace.id}_schemas"
        if cache_key in self._schema_cache:
            del self._schema_cache[cache_key]

        return workspace

    async def sync_s3_schema_to_metadata(
        self, db: AsyncSession, workspace: Workspace, schema_name: str, prefix: str = DEFAULT_SCHEMA_S3_PATH
    ) -> Dict[str, Any]:
        """
        Sync a specific schema from S3 to workspace metadata.

        Args:
            db: Database session
            workspace: The workspace to sync schemas for
            schema_name: Name of the schema to sync
            prefix: S3 prefix to search for schemas

        Returns:
            Updated schema configuration
        """
        if not PANDERA_AVAILABLE:
            raise RuntimeError("Pandera is not available - schema operations require the extralit package")

        bucket_name = workspace.name
        schema_path = f"{prefix.rstrip('/')}/{schema_name}.json"

        try:
            # Get schema file from S3
            file_response = files.get_object(self.minio_client, bucket_name, schema_path, include_versions=True)

            # Parse schema to validate it
            schema_data = json.loads(file_response.response.data.decode("utf-8"))
            from_json(BytesIO(json.dumps(schema_data).encode("utf-8")))

            # Get current schema configuration
            current_config = await self.get_workspace_schema_configuration(workspace)
            schemas = current_config.get("schemas", [])

            # Check if schema is singleton
            is_singleton = any(
                check.get("name") == "singleton" and check.get("statistics", {}).get("enabled", True)
                for check in schema_data.get("checks", [])
            )

            # Find existing schema or create new entry
            existing_schema = None
            for i, s in enumerate(schemas):
                if s["name"] == schema_name:
                    existing_schema = i
                    break

            schema_entry = {
                "name": schema_name,
                "is_singleton": is_singleton,
                "s3_path": schema_path,
                "version_id": file_response.metadata.version_id,
                "dependencies": [],  # TODO: Extract dependencies from schema
            }

            if existing_schema is not None:
                schemas[existing_schema] = schema_entry
            else:
                schemas.append(schema_entry)

            # Update workspace metadata
            updated_config = {"schemas": schemas, "last_sync": datetime.utcnow().isoformat()}

            await self.update_workspace_schema_configuration(db, workspace, updated_config)

            return updated_config

        except Exception as e:
            _LOGGER.error(f"Error syncing schema {schema_name} from S3 for workspace {workspace.name}: {e}")
            raise

    async def sync_all_s3_schemas_to_metadata(
        self, db: AsyncSession, workspace: Workspace, prefix: str = DEFAULT_SCHEMA_S3_PATH
    ) -> Dict[str, Any]:
        """
        Sync all schemas from S3 to workspace metadata.

        Args:
            db: Database session
            workspace: The workspace to sync schemas for
            prefix: S3 prefix to search for schemas

        Returns:
            Updated schema configuration
        """
        if not PANDERA_AVAILABLE:
            raise RuntimeError("Pandera is not available - schema operations require the extralit package")

        bucket_name = workspace.name

        try:
            # List all schema files in S3
            objects_response = files.list_objects(
                self.minio_client, bucket_name, prefix=prefix, include_version=False, recursive=True
            )

            schemas = []
            for obj in objects_response.objects:
                if obj.object_name.endswith(".json"):
                    schema_name = obj.object_name.split("/")[-1].replace(".json", "")

                    try:
                        # Get and parse schema
                        file_response = files.get_object(self.minio_client, bucket_name, obj.object_name)

                        schema_data = json.loads(file_response.response.data.decode("utf-8"))

                        # Check if schema is singleton
                        is_singleton = any(
                            check.get("name") == "singleton" and check.get("statistics", {}).get("enabled", True)
                            for check in schema_data.get("checks", [])
                        )

                        schema_entry = {
                            "name": schema_name,
                            "is_singleton": is_singleton,
                            "s3_path": obj.object_name,
                            "version_id": file_response.metadata.version_id,
                            "dependencies": [],  # TODO: Extract dependencies from schema
                        }

                        schemas.append(schema_entry)

                    except Exception as e:
                        _LOGGER.warning(f"Skipping schema {schema_name} due to error: {e}")
                        continue

            # Update workspace metadata
            updated_config = {"schemas": schemas, "last_sync": datetime.utcnow().isoformat()}

            await self.update_workspace_schema_configuration(db, workspace, updated_config)

            return updated_config

        except Exception as e:
            _LOGGER.error(f"Error syncing all schemas from S3 for workspace {workspace.name}: {e}")
            raise

    async def create_schema_structure_from_metadata(self, workspace: Workspace) -> Optional["SchemaStructure"]:
        """
        Create a SchemaStructure object from workspace metadata.

        Args:
            workspace: The workspace to create SchemaStructure for

        Returns:
            SchemaStructure object or None if extralit package not available
        """
        if not EXTRALIT_AVAILABLE or not PANDERA_AVAILABLE:
            _LOGGER.warning("SchemaStructure not available - extralit package or pandera not installed")
            return None

        # Check cache first
        cache_key = f"workspace_{workspace.id}_schemas"
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        schema_config = await self.get_workspace_schema_configuration(workspace)
        schemas_data = schema_config.get("schemas", [])

        if not schemas_data:
            return SchemaStructure(schemas=[])

        bucket_name = workspace.name
        schemas = []
        singleton_schema = None

        for schema_data in schemas_data:
            try:
                # Get schema from S3
                file_response = files.get_object(
                    self.minio_client, bucket_name, schema_data["s3_path"], version_id=schema_data.get("version_id")
                )

                # Parse schema
                schema_json = file_response.response.data.decode("utf-8")
                schema = from_json(BytesIO(schema_json.encode("utf-8")))

                schemas.append(schema)

                if schema_data.get("is_singleton"):
                    singleton_schema = schema

            except Exception as e:
                _LOGGER.warning(f"Failed to load schema {schema_data['name']}: {e}")
                continue

        schema_structure = SchemaStructure(schemas=schemas, singleton_schema=singleton_schema)

        # Cache the result
        self._schema_cache[cache_key] = schema_structure

        return schema_structure

    async def validate_schema(self, workspace: Workspace, schema_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a specific schema using Pandera.

        Args:
            workspace: The workspace containing the schema
            schema_name: Name of the schema to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not PANDERA_AVAILABLE:
            return False, "Pandera is not available - schema validation requires the extralit package"

        try:
            schema_config = await self.get_workspace_schema_configuration(workspace)
            schema_data = None

            for s in schema_config.get("schemas", []):
                if s["name"] == schema_name:
                    schema_data = s
                    break

            if not schema_data:
                return False, f"Schema {schema_name} not found in workspace configuration"

            # Get schema from S3
            bucket_name = workspace.name
            file_response = files.get_object(
                self.minio_client, bucket_name, schema_data["s3_path"], version_id=schema_data.get("version_id")
            )

            # Parse and validate schema
            schema_json = file_response.response.data.decode("utf-8")
            schema = from_json(BytesIO(schema_json.encode("utf-8")))

            # Basic validation - schema should have columns
            if not schema.columns:
                return False, "Schema has no columns defined"

            return True, None

        except Exception as e:
            return False, str(e)

    async def validate_all_schemas(self, workspace: Workspace) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        Validate all schemas in a workspace.

        Args:
            workspace: The workspace to validate schemas for

        Returns:
            Dict mapping schema names to validation results
        """
        schema_config = await self.get_workspace_schema_configuration(workspace)
        schemas_data = schema_config.get("schemas", [])

        results = {}
        for schema_data in schemas_data:
            schema_name = schema_data["name"]
            is_valid, error = await self.validate_schema(workspace, schema_name)
            results[schema_name] = (is_valid, error)

        return results

    def clear_cache(self, workspace_id: Optional[UUID] = None):
        """
        Clear the schema cache.

        Args:
            workspace_id: If provided, clear cache only for this workspace.
                         If None, clear all cache.
        """
        if workspace_id:
            cache_key = f"workspace_{workspace_id}_schemas"
            if cache_key in self._schema_cache:
                del self._schema_cache[cache_key]
        else:
            self._schema_cache.clear()
