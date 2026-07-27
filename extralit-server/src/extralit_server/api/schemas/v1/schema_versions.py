from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SchemaVersionCreate(BaseModel):
    """A new schema version. `body` is a Pandera `DataFrameSchema.to_json()` payload."""

    body: str
    # Per-column widget overlay; Pandera's to_json drops Column.metadata, so this rides
    # alongside and lands in each derived Field's settings["review"].
    review_widgets: dict[str, dict[str, Any]] = Field(default_factory=dict)


class SchemaVersionRead(BaseModel):
    id: UUID
    dataset_id: UUID
    version: int
    object_key: str
    object_version_id: str | None
    etag: str
    checksum: str
    parent_version_id: UUID | None
    created_by: UUID | None
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
