#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from datetime import datetime
from optparse import Option
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class Workspace(BaseModel):
    id: UUID
    name: str
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    id: Optional[UUID] = None
    name: str = Field(min_length=1)


class Workspaces(BaseModel):
    items: List[Workspace]


class WorkspaceUserCreate(BaseModel):
    user_id: UUID


class SchemaConfiguration(BaseModel):
    """Schema configuration for a single schema within a workspace."""
    name: str = Field(description="Name of the schema")
    is_singleton: bool = Field(description="Whether this is a singleton schema")
    s3_path: str = Field(description="S3 path to the schema file")
    version_id: Optional[str] = Field(None, description="S3 version ID of the schema file")
    dependencies: List[str] = Field(default_factory=list, description="List of schema names this schema depends on")


class WorkspaceSchemaConfiguration(BaseModel):
    """Complete schema configuration for a workspace."""
    schemas: List[SchemaConfiguration] = Field(default_factory=list, description="List of schemas in the workspace")
    last_sync: Optional[str] = Field(None, description="ISO timestamp of last sync with S3")


class WorkspaceSchemaConfigurationUpdate(BaseModel):
    """Request body for updating workspace schema configuration."""
    schema_configuration: WorkspaceSchemaConfiguration = Field(description="New schema configuration")


class SchemaValidationResult(BaseModel):
    """Result of schema validation."""
    schema_name: str = Field(description="Name of the validated schema")
    is_valid: bool = Field(description="Whether the schema is valid")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")


class WorkspaceSchemaValidationResponse(BaseModel):
    """Response containing validation results for all schemas in a workspace."""
    validation_results: List[SchemaValidationResult] = Field(description="Validation results for each schema")
    all_valid: bool = Field(description="Whether all schemas are valid")


class SchemaSyncRequest(BaseModel):
    """Request body for syncing a specific schema from S3."""
    prefix: str = Field(default="schemas/", description="S3 prefix to search for schemas")


class SchemaSyncResponse(BaseModel):
    """Response after syncing schemas from S3."""
    schema_configuration: WorkspaceSchemaConfiguration = Field(description="Updated schema configuration")
    schemas_synced: int = Field(description="Number of schemas that were synced")
    message: str = Field(description="Success message")
