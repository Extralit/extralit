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
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, conlist, constr, model_validator

from extralit_server.api.schemas.v1.commons import UpdateSchema
from extralit_server.api.schemas.v1.fields import FieldName
from extralit_server.enums import OptionsOrder, QuestionType
from extralit_server.settings import settings

try:
    from typing import Annotated
except ImportError:
    from typing import Annotated

QUESTION_CREATE_NAME_MIN_LENGTH = 1
QUESTION_CREATE_NAME_MAX_LENGTH = 200

QUESTION_CREATE_TITLE_MIN_LENGTH = 1
QUESTION_CREATE_TITLE_MAX_LENGTH = 500

QUESTION_CREATE_DESCRIPTION_MIN_LENGTH = 1
QUESTION_CREATE_DESCRIPTION_MAX_LENGTH = 1000

VALUE_TEXT_OPTION_VALUE_MIN_LENGTH = 1
VALUE_TEXT_OPTION_VALUE_MAX_LENGTH = 200
VALUE_TEXT_OPTION_TEXT_MIN_LENGTH = 1
VALUE_TEXT_OPTION_TEXT_MAX_LENGTH = 500
VALUE_TEXT_OPTION_DESCRIPTION_MIN_LENGTH = 1
VALUE_TEXT_OPTION_DESCRIPTION_MAX_LENGTH = 1000

LABEL_SELECTION_OPTIONS_MIN_ITEMS = 0
LABEL_SELECTION_MIN_VISIBLE_OPTIONS = 3

RANKING_OPTIONS_MIN_ITEMS = 2
RANKING_OPTIONS_MAX_ITEMS = 50

RATING_OPTIONS_MIN_ITEMS = 2
RATING_OPTIONS_MAX_ITEMS = 11
RATING_VALUE_GREATER_THAN_OR_EQUAL = 0
RATING_VALUE_LESS_THAN_OR_EQUAL = 10

SPAN_OPTIONS_MIN_ITEMS = 1
SPAN_MIN_VISIBLE_OPTIONS = 3


class UniqueValuesCheckerMixin(BaseModel):
    @model_validator(mode="after")
    @classmethod
    def check_unique_values(cls, instance: "UniqueValuesCheckerMixin") -> "UniqueValuesCheckerMixin":
        options = instance.options or []
        seen = set()
        duplicates = set()
        for option in options:
            if option.value in seen:
                duplicates.add(option.value)
            else:
                seen.add(option.value)
        if duplicates:
            raise ValueError(f"Option values must be unique, found duplicates: {duplicates}")
        return instance


# Option-based settings
class OptionSettings(BaseModel):
    value: str
    text: str
    description: str | None = None


class OptionSettingsCreate(BaseModel):
    value: constr(
        min_length=VALUE_TEXT_OPTION_VALUE_MIN_LENGTH,
        max_length=VALUE_TEXT_OPTION_VALUE_MAX_LENGTH,
    )
    text: constr(
        min_length=VALUE_TEXT_OPTION_TEXT_MIN_LENGTH,
        max_length=VALUE_TEXT_OPTION_TEXT_MAX_LENGTH,
    )
    description: (
        constr(min_length=VALUE_TEXT_OPTION_DESCRIPTION_MIN_LENGTH, max_length=VALUE_TEXT_OPTION_DESCRIPTION_MAX_LENGTH)
        | None
    ) = None


# Text question
class TextQuestionSettings(BaseModel):
    type: Literal[QuestionType.text]
    use_markdown: bool = False
    use_table: bool = False


class TextQuestionSettingsCreate(BaseModel):
    type: Literal[QuestionType.text]
    use_markdown: bool = False
    use_table: bool = False


class TextQuestionSettingsUpdate(UpdateSchema):
    type: Literal[QuestionType.text]
    use_markdown: bool | None = None
    use_table: bool | None = None

    __non_nullable_fields__ = {"use_markdown", "use_table"}


# Rating question
class RatingQuestionSettingsOption(BaseModel):
    value: int


class RatingQuestionSettingsOptionCreate(BaseModel):
    value: int = Field(ge=RATING_VALUE_GREATER_THAN_OR_EQUAL, le=RATING_VALUE_LESS_THAN_OR_EQUAL)


class RatingQuestionSettings(BaseModel):
    type: Literal[QuestionType.rating]
    options: list[RatingQuestionSettingsOption]


class RatingQuestionSettingsCreate(UniqueValuesCheckerMixin):
    type: Literal[QuestionType.rating]
    options: list[RatingQuestionSettingsOptionCreate] = Field(
        min_length=RATING_OPTIONS_MIN_ITEMS,
        max_length=RATING_OPTIONS_MAX_ITEMS,
    )


class RatingQuestionSettingsUpdate(UpdateSchema):
    type: Literal[QuestionType.rating]


# Label selection question
class LabelSelectionQuestionSettings(BaseModel):
    type: Literal[QuestionType.label_selection, QuestionType.dynamic_label_selection]
    options: list[OptionSettings]
    visible_options: int | None = None


class LabelSelectionQuestionSettingsCreate(UniqueValuesCheckerMixin):
    type: Literal[QuestionType.label_selection, QuestionType.dynamic_label_selection]
    options: conlist(
        item_type=OptionSettingsCreate,
        min_length=LABEL_SELECTION_OPTIONS_MIN_ITEMS,
        max_length=settings.label_selection_options_max_items,
    )
    visible_options: int | None = Field(None, ge=LABEL_SELECTION_MIN_VISIBLE_OPTIONS)

    @model_validator(mode="after")
    @classmethod
    def check_visible_options_value(
        cls, instance: "LabelSelectionQuestionSettingsCreate"
    ) -> "LabelSelectionQuestionSettingsCreate":
        visible_options = instance.visible_options
        if visible_options is not None:
            num_options = len(instance.options)
            if visible_options > num_options and "dynamic" not in instance.type:
                raise ValueError(
                    "the value for 'visible_options' must be less or equal to the number of items in 'options'"
                    f" ({num_options})"
                )

        return instance


class LabelSelectionSettingsUpdate(UpdateSchema):
    type: Literal[QuestionType.label_selection, QuestionType.dynamic_label_selection]
    visible_options: int | None = Field(None)
    options: (
        conlist(
            item_type=OptionSettings,
            min_length=LABEL_SELECTION_OPTIONS_MIN_ITEMS,
            max_length=settings.label_selection_options_max_items,
        )
        | None
    ) = None


# Multi-label selection question
class MultiLabelSelectionQuestionSettings(LabelSelectionQuestionSettings):
    type: Literal[QuestionType.multi_label_selection, QuestionType.dynamic_multi_label_selection]
    options_order: OptionsOrder = OptionsOrder.natural


class MultiLabelSelectionQuestionSettingsCreate(LabelSelectionQuestionSettingsCreate):
    type: Literal[QuestionType.multi_label_selection, QuestionType.dynamic_multi_label_selection]
    options_order: OptionsOrder = OptionsOrder.natural


class MultiLabelSelectionQuestionSettingsUpdate(LabelSelectionSettingsUpdate):
    type: Literal[QuestionType.multi_label_selection, QuestionType.dynamic_multi_label_selection]
    options_order: OptionsOrder | None = None

    __non_nullable_fields__ = {"options_order"}


# Ranking question
class RankingQuestionSettings(BaseModel):
    type: Literal[QuestionType.ranking]
    options: list[OptionSettings]


class RankingQuestionSettingsCreate(UniqueValuesCheckerMixin):
    type: Literal[QuestionType.ranking]
    options: conlist(
        item_type=OptionSettingsCreate,
        min_length=RANKING_OPTIONS_MIN_ITEMS,
        max_length=RANKING_OPTIONS_MAX_ITEMS,
    )


class RankingQuestionSettingsUpdate(UpdateSchema):
    type: Literal[QuestionType.ranking]


# Span question
class SpanQuestionSettings(BaseModel):
    type: Literal[QuestionType.span]
    field: str
    options: list[OptionSettings]
    visible_options: int | None = None
    # These attributes are read-only for now
    allow_overlapping: bool = Field(default=False, description="Allow spans overlapping")
    allow_character_annotation: bool = Field(default=True, description="Allow character-level annotation")


class SpanQuestionSettingsCreate(UniqueValuesCheckerMixin):
    type: Literal[QuestionType.span]
    field: FieldName
    options: conlist(
        item_type=OptionSettingsCreate,
        min_length=SPAN_OPTIONS_MIN_ITEMS,
        max_length=settings.span_options_max_items,
    )
    visible_options: int | None = Field(None, ge=SPAN_MIN_VISIBLE_OPTIONS)
    allow_overlapping: bool = False

    @model_validator(mode="after")
    @classmethod
    def check_visible_options_value(cls, instance: "SpanQuestionSettingsCreate") -> "SpanQuestionSettingsCreate":
        visible_options = instance.visible_options
        if visible_options is not None:
            num_options = len(instance.options)
            if visible_options > num_options:
                raise ValueError(
                    "the value for 'visible_options' must be less or equal to the number of items in 'options'"
                    f" ({num_options})"
                )

        return instance


class SpanQuestionSettingsUpdate(UpdateSchema):
    type: Literal[QuestionType.span]
    options: (
        conlist(item_type=OptionSettings, min_length=SPAN_OPTIONS_MIN_ITEMS, max_length=settings.span_options_max_items)
        | None
    ) = None
    visible_options: int | None = Field(None, ge=SPAN_MIN_VISIBLE_OPTIONS)
    allow_overlapping: bool | None = None


class TableQuestionSettings(BaseModel):
    type: Literal[QuestionType.table]


class TableQuestionSettingsCreate(BaseModel):
    type: Literal[QuestionType.table]


class TableQuestionSettingsUpdate(UpdateSchema):
    type: Literal[QuestionType.table]

    __non_nullable_fields__ = {}


QuestionSettings = Annotated[
    TextQuestionSettings
    | RatingQuestionSettings
    | LabelSelectionQuestionSettings
    | MultiLabelSelectionQuestionSettings
    | RankingQuestionSettings
    | SpanQuestionSettings
    | TableQuestionSettings,
    Field(..., discriminator="type"),
]

QuestionName = Annotated[
    constr(
        min_length=QUESTION_CREATE_NAME_MIN_LENGTH,
        max_length=QUESTION_CREATE_NAME_MAX_LENGTH,
    ),
    Field(..., description="The name of the question"),
]

QuestionTitle = Annotated[
    constr(
        min_length=QUESTION_CREATE_TITLE_MIN_LENGTH,
        max_length=QUESTION_CREATE_TITLE_MAX_LENGTH,
    ),
    Field(..., description="The title of the question"),
]

QuestionDescription = Annotated[
    constr(
        min_length=QUESTION_CREATE_DESCRIPTION_MIN_LENGTH,
        max_length=QUESTION_CREATE_DESCRIPTION_MAX_LENGTH,
    ),
    Field(..., description="The description of the question"),
]

QuestionSettingsCreate = Annotated[
    TextQuestionSettingsCreate
    | RatingQuestionSettingsCreate
    | LabelSelectionQuestionSettingsCreate
    | MultiLabelSelectionQuestionSettingsCreate
    | RankingQuestionSettingsCreate
    | SpanQuestionSettingsCreate
    | TableQuestionSettingsCreate,
    Field(discriminator="type"),
]

QuestionSettingsUpdate = Annotated[
    TextQuestionSettingsUpdate
    | RatingQuestionSettingsUpdate
    | LabelSelectionSettingsUpdate
    | MultiLabelSelectionQuestionSettingsUpdate
    | RankingQuestionSettingsUpdate
    | SpanQuestionSettingsUpdate
    | TableQuestionSettingsUpdate,
    Field(..., discriminator="type"),
]


class Question(BaseModel):
    id: UUID
    name: str
    title: str
    description: str | None = None
    required: bool
    settings: QuestionSettings
    dataset_id: UUID
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Questions(BaseModel):
    items: list[Question]


class QuestionCreate(BaseModel):
    name: QuestionName
    title: QuestionTitle
    description: QuestionDescription | None = None
    required: bool | None = None
    settings: QuestionSettingsCreate


class QuestionUpdate(UpdateSchema):
    title: QuestionTitle | None = None
    description: QuestionDescription | None = None
    settings: QuestionSettingsUpdate | None = None

    __non_nullable_fields__ = {"title", "settings"}
