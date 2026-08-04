from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# A generous ceiling on the Pandera body. This is the payload the server parses in-process
# and then uploads whole, so one request sizes both the parse and the object write -- worth
# bounding even behind an owner/admin-only route. 1 MiB sits far above any real schema (a
# 500-column DataFrameSchema serializes to well under 100 KiB); it exists to catch a runaway
# or malformed client, not to express a product limit. Bounding the request as a whole
# belongs in a request-size limit at the ASGI layer, which this codebase does not have yet.
SCHEMA_VERSION_BODY_MAX_LENGTH = 1024 * 1024


class SchemaVersionCreate(BaseModel):
    """A new schema version. `body` is a Pandera `DataFrameSchema.to_json()` payload."""

    body: str = Field(..., max_length=SCHEMA_VERSION_BODY_MAX_LENGTH)
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
