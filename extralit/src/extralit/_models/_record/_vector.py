import re

from pydantic import field_validator

from extralit._models import ResourceModel

__all__ = ["VectorModel", "VectorValue"]

VectorValue = list[float]


class VectorModel(ResourceModel):
    name: str
    vector_values: VectorValue

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        """Validate the name of the vector is url safe"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", value):
            raise ValueError("Vector name must be url safe")
        return value
