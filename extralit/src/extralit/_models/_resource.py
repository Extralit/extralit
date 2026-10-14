from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_serializer


class ResourceModel(BaseModel):
    """Base model for all resources (DatasetModel, WorkspaceModel, UserModel, etc.)"""

    id: Optional[UUID] = None
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("inserted_at", "updated_at", when_used="unless-none")
    def serialize_datetime(value: datetime) -> str:
        return value.isoformat()

    @field_serializer("id", when_used="unless-none")
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    def __hash__(self) -> int:
        return hash(self.model_dump_json())
