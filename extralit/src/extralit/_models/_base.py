from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, field_serializer


class ResourceModel(BaseModel):
    """Base model for all resources (DatasetModel, WorkspaceModel, UserModel, etc.)"""

    id: Optional[UUID] = uuid4()
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("inserted_at", "updated_at", when_used="unless-none")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("id", when_used="unless-none")
    def serialize_id(self, value: UUID) -> str:
        return str(value)
