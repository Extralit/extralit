from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, constr

from extralit_server.enums import SchemaKind, SchemaStatus

SchemaName = constr(min_length=1, max_length=200)


class SchemaCreate(BaseModel):
    name: SchemaName
    kind: SchemaKind = SchemaKind.table
    workspace_id: UUID
    settings: dict[str, Any] = Field(default_factory=dict)


class SchemaUpdate(BaseModel):
    name: SchemaName | None = None
    settings: dict[str, Any] | None = None


class SchemaVersionCreate(BaseModel):
    body: str = Field(..., description="Pandera DataFrameSchema serialized via .to_json()")
    # Per-column review widgets carried out-of-band (column name -> widget config); see spec §13.
    # Pandera's to_json drops Column.metadata, so the review widget cannot live in `body`.
    review_widgets: dict[str, dict[str, Any]] = Field(default_factory=dict)


class SchemaVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schema_id: UUID
    version: int
    object_key: str
    object_version_id: str | None
    etag: str
    checksum: str
    parent_version_id: UUID | None
    columns_cache: list[dict[str, Any]]
    review_widgets: dict[str, dict[str, Any]]
    inserted_at: datetime


class SchemaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: SchemaKind
    status: SchemaStatus
    current_version_id: UUID | None
    settings: dict[str, Any]
    workspace_id: UUID
    inserted_at: datetime
    updated_at: datetime


class Schemas(BaseModel):
    items: list[SchemaRead]
