from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, constr

from extralit_server.enums import V2RecordStatus

RECORDS_BULK_UPSERT_MIN_ITEMS = 1
RECORDS_BULK_UPSERT_MAX_ITEMS = 500  # mirrors v1 RECORDS_BULK_CREATE_MAX_ITEMS
LIST_RECORDS_LIMIT_DEFAULT = 50  # mirrors v1 LIST_DATASET_RECORDS_LIMIT_DEFAULT
LIST_RECORDS_LIMIT_LE = 1000  # mirrors v1 LIST_DATASET_RECORDS_LIMIT_LE
DELETE_RECORDS_LIMIT = 100  # mirrors v1 DELETE_DATASET_RECORDS_LIMIT

Reference = constr(min_length=1, max_length=500)


class RecordUpsert(BaseModel):
    fields: dict[str, Any]
    reference: Reference
    external_id: str | None = None
    metadata: dict[str, Any] | None = None
    status: V2RecordStatus | None = None
    schema_version_id: UUID | None = Field(
        default=None, description="Pin to a specific version; defaults to the schema's current_version_id"
    )


class RecordsBulkUpsert(BaseModel):
    items: list[RecordUpsert] = Field(
        ..., min_length=RECORDS_BULK_UPSERT_MIN_ITEMS, max_length=RECORDS_BULK_UPSERT_MAX_ITEMS
    )


class RecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    schema_id: UUID
    schema_version_id: UUID
    reference: str
    external_id: str | None
    fields: dict[str, Any]
    # ORM attr is `metadata_` (column "metadata"); accept either name, serialize as `metadata`.
    metadata: dict[str, Any] | None = Field(default=None, validation_alias=AliasChoices("metadata_", "metadata"))
    status: V2RecordStatus
    inserted_at: datetime
    updated_at: datetime


class Records(BaseModel):
    items: list[RecordRead]
    total: int


class ReferenceGroup(BaseModel):
    # Flattened schema_id/schema_name (not a nested `schema:` field) to avoid pydantic's
    # BaseModel.schema() attribute shadowing.
    schema_id: UUID
    schema_name: str
    records: list[RecordRead]


class ReferenceView(BaseModel):
    reference: str
    groups: list[ReferenceGroup]
    total_records: int
