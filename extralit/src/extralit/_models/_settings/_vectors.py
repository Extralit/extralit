from typing import Optional
from uuid import UUID

from pydantic import field_serializer, field_validator
from pydantic_core.core_schema import ValidationInfo

from extralit._helpers import log_message
from extralit._models import ResourceModel


class VectorFieldModel(ResourceModel):
    name: str
    title: Optional[str] = None
    dimensions: int
    dataset_id: Optional[UUID] = None

    @field_serializer("id", "dataset_id", when_used="unless-none")
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    @field_validator("title")
    @classmethod
    def _title_default(cls, title: str, info: ValidationInfo) -> str:
        data = info.data
        validated_title = title or data["name"]
        log_message(f"TextField title is {validated_title}")
        return validated_title

    @field_validator("dimensions")
    @classmethod
    def _dimension_gt_zero(cls, dimensions):
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than 0")
        return dimensions
