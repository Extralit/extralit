from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_serializer

from extralit._models import ResourceModel

__all__ = ["DatasetModel"]

from extralit._models._settings._mapping import DatasetMappingModel
from extralit._models._settings._task_distribution import TaskDistributionModel


class DatasetModel(ResourceModel):
    name: str
    status: Literal["draft", "ready"] = "draft"

    guidelines: Optional[str] = None
    allow_extra_metadata: bool = True  # Ideally, the default value should be provided by the server
    distribution: Optional[TaskDistributionModel] = None
    mapping: Optional[DatasetMappingModel] = Field(None, repr=False)
    workspace_id: Optional[UUID] = None
    last_activity_at: Optional[datetime] = None

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_serializer("last_activity_at", when_used="unless-none")
    def serialize_last_activity_at(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("workspace_id", when_used="unless-none")
    def serialize_workspace_id(self, value: UUID) -> str:
        return str(value)
