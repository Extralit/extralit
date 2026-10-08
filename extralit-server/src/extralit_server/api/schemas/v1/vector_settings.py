from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, constr

from extralit_server.api.schemas.v1.commons import UpdateSchema
from extralit_server.errors.future import UnprocessableEntityError

VECTOR_SETTINGS_CREATE_NAME_MIN_LENGTH = 1
VECTOR_SETTINGS_CREATE_NAME_MAX_LENGTH = 200

VECTOR_SETTINGS_CREATE_TITLE_MIN_LENGTH = 1
VECTOR_SETTINGS_CREATE_TITLE_MAX_LENGTH = 500


VectorSettingsTitle = Annotated[
    constr(
        min_length=VECTOR_SETTINGS_CREATE_TITLE_MIN_LENGTH,
        max_length=VECTOR_SETTINGS_CREATE_TITLE_MAX_LENGTH,
    ),
    Field(..., description="The title of the vector settings"),
]


class VectorSettings(BaseModel):
    id: UUID
    name: str
    title: str
    dimensions: int
    dataset_id: UUID
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    def check_vector(self, value: list[float]) -> None:
        num_elements = len(value)

        if num_elements != self.dimensions:
            raise UnprocessableEntityError(f"vector must have {self.dimensions} elements, got {num_elements} elements")


class VectorsSettings(BaseModel):
    items: list[VectorSettings]


class VectorSettingsCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=VECTOR_SETTINGS_CREATE_NAME_MIN_LENGTH,
        max_length=VECTOR_SETTINGS_CREATE_NAME_MAX_LENGTH,
        description="The title of the vector settings",
    )
    title: VectorSettingsTitle
    dimensions: PositiveInt


class VectorSettingsUpdate(UpdateSchema):
    title: VectorSettingsTitle | None

    __non_nullable_fields__ = {"title"}
