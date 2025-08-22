# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, constr, field_validator, model_validator

from extralit_server.api.schemas.v1.commons import UpdateSchema
from extralit_server.enums import MetadataPropertyType

FLOAT_METADATA_METRICS_PRECISION = 5

METADATA_PROPERTY_CREATE_NAME_MIN_LENGTH = 1
METADATA_PROPERTY_CREATE_NAME_MAX_LENGTH = 200

METADATA_PROPERTY_CREATE_TITLE_MIN_LENGTH = 1
METADATA_PROPERTY_CREATE_TITLE_MAX_LENGTH = 500

TERMS_METADATA_PROPERTY_VALUES_MIN_ITEMS = 1
TERMS_METADATA_PROPERTY_VALUES_MAX_ITEMS = 250

try:
    from typing import Annotated
except ImportError:
    from typing import Annotated


class TermsMetadataMetrics(BaseModel):
    class TermCount(BaseModel):
        term: Any
        count: int

    type: Literal[MetadataPropertyType.terms] = MetadataPropertyType.terms
    total: int
    values: list[TermCount] = Field(default_factory=list)


NT = TypeVar("NT", int, float)


class NumericMetadataMetrics(BaseModel, Generic[NT]):
    min: NT | None = None
    max: NT | None = None


class IntegerMetadataMetrics(NumericMetadataMetrics[int]):
    type: Literal[MetadataPropertyType.integer] = MetadataPropertyType.integer


class FloatMetadataMetrics(NumericMetadataMetrics[float]):
    type: Literal[MetadataPropertyType.float] = MetadataPropertyType.float

    @field_validator("min", "max")
    @classmethod
    def round_result(cls, v: float | None) -> float | None:
        if v is not None:
            return round(v, FLOAT_METADATA_METRICS_PRECISION)
        return v


MetadataMetrics = Annotated[
    TermsMetadataMetrics | IntegerMetadataMetrics | FloatMetadataMetrics,
    Field(..., discriminator="type"),
]


class TermsMetadataProperty(BaseModel):
    type: Literal[MetadataPropertyType.terms]
    values: list[Any] | None = None


class IntegerMetadataProperty(BaseModel):
    type: Literal[MetadataPropertyType.integer]
    min: int | None = None
    max: int | None = None


class FloatMetadataProperty(BaseModel):
    type: Literal[MetadataPropertyType.float]
    min: float | None = None
    max: float | None = None


MetadataPropertySettings = Annotated[
    TermsMetadataProperty | IntegerMetadataProperty | FloatMetadataProperty,
    Field(..., discriminator="type"),
]

MetadataPropertyName = Annotated[
    str,
    Field(
        ...,
        min_length=METADATA_PROPERTY_CREATE_NAME_MIN_LENGTH,
        max_length=METADATA_PROPERTY_CREATE_NAME_MAX_LENGTH,
    ),
]

MetadataPropertyTitle = Annotated[
    constr(min_length=METADATA_PROPERTY_CREATE_TITLE_MIN_LENGTH, max_length=METADATA_PROPERTY_CREATE_TITLE_MAX_LENGTH),
    Field(..., description="The title of the metadata property"),
]


class NumericMetadataProperty(BaseModel, Generic[NT]):
    min: NT | None = None
    max: NT | None = None

    @model_validator(mode="after")
    @classmethod
    def check_bounds(cls, instance: "NumericMetadataProperty") -> "NumericMetadataProperty":
        min = instance.min
        max = instance.max

        if min is not None and max is not None and min >= max:
            raise ValueError(f"'min' ({min}) must be lower than 'max' ({max})")

        return instance


class TermsMetadataPropertyCreate(BaseModel):
    type: Literal[MetadataPropertyType.terms]
    values: list[Any] | None = Field(
        None,
        min_length=TERMS_METADATA_PROPERTY_VALUES_MIN_ITEMS,
        max_length=TERMS_METADATA_PROPERTY_VALUES_MAX_ITEMS,
    )


class IntegerMetadataPropertyCreate(NumericMetadataProperty[int]):
    type: Literal[MetadataPropertyType.integer]


class FloatMetadataPropertyCreate(NumericMetadataProperty[float]):
    type: Literal[MetadataPropertyType.float]


MetadataPropertySettingsCreate = Annotated[
    TermsMetadataPropertyCreate | IntegerMetadataPropertyCreate | FloatMetadataPropertyCreate,
    Field(..., discriminator="type"),
]


class MetadataProperty(BaseModel):
    id: UUID
    name: str
    title: str
    settings: MetadataPropertySettings
    visible_for_annotators: bool
    dataset_id: UUID
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetadataProperties(BaseModel):
    items: list[MetadataProperty]


class MetadataPropertyCreate(BaseModel):
    name: MetadataPropertyName
    title: MetadataPropertyTitle
    settings: MetadataPropertySettingsCreate
    visible_for_annotators: bool = True


class MetadataPropertyUpdate(UpdateSchema):
    title: MetadataPropertyTitle | None = None
    visible_for_annotators: bool | None = None

    __non_nullable_fields__ = {"title", "visible_for_annotators"}
