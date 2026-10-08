from typing import Annotated, ClassVar, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from extralit._models import ResourceModel

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class LabelQuestionSettings(BaseModel):
    type: Literal["label_selection"] = "label_selection"

    _MIN_VISIBLE_OPTIONS: ClassVar[int] = 3

    options: list[dict[str, Optional[str]]] = Field(default_factory=list, validate_default=True)
    visible_options: Optional[int] = Field(None, validate_default=True, ge=_MIN_VISIBLE_OPTIONS)
    strict: bool = Field(True, description="Whether selections must be limited to predefined options")

    @field_validator("options", mode="before")
    @classmethod
    def __labels_are_unique(cls, options: list[dict[str, Optional[str]]]) -> list[dict[str, Optional[str]]]:
        """Ensure that labels are unique"""

        unique_labels = list({option["value"] for option in options})
        if len(unique_labels) != len(options):
            raise ValueError("All labels must be unique")
        return options

    @model_validator(mode="after")
    def __validate_visible_options(self) -> "Self":
        if self.visible_options is None and self.options and len(self.options) >= self._MIN_VISIBLE_OPTIONS:
            self.visible_options = len(self.options)
        return self


class MultiLabelQuestionSettings(LabelQuestionSettings):
    type: Literal["multi_label_selection"] = "multi_label_selection"
    options_order: Literal["natural", "suggestion"] = Field("natural", description="The order of the labels in the UI.")


class RankingQuestionSettings(BaseModel):
    type: Literal["ranking"] = "ranking"

    options: list[dict[str, Optional[str]]] = Field(default_factory=list, validate_default=True)

    @field_validator("options", mode="before")
    @classmethod
    def __values_are_unique(cls, options: list[dict[str, Optional[str]]]) -> list[dict[str, Optional[str]]]:
        """Ensure that values are unique"""

        unique_values = list({option["value"] for option in options})
        if len(unique_values) != len(options):
            raise ValueError("All values must be unique")

        return options


class RatingQuestionSettings(BaseModel):
    type: Literal["rating"] = "rating"

    options: list[dict] = Field(..., validate_default=True)

    @field_validator("options", mode="before")
    @classmethod
    def __values_are_unique(cls, options: list[dict]) -> list[dict]:
        """Ensure that values are unique"""

        unique_values = list({option["value"] for option in options})
        if len(unique_values) != len(options):
            raise ValueError("All values must be unique")

        return options


class SpanQuestionSettings(BaseModel):
    type: Literal["span"] = "span"

    _MIN_VISIBLE_OPTIONS: ClassVar[int] = 3

    allow_overlapping: bool = False
    field: Optional[str] = None
    options: list[dict[str, Optional[str]]] = Field(default_factory=list, validate_default=True)
    visible_options: Optional[int] = Field(None, validate_default=True, ge=_MIN_VISIBLE_OPTIONS)

    @field_validator("options", mode="before")
    @classmethod
    def __values_are_unique(cls, options: list[dict[str, Optional[str]]]) -> list[dict[str, Optional[str]]]:
        """Ensure that values are unique"""

        unique_values = list({option["value"] for option in options})
        if len(unique_values) != len(options):
            raise ValueError("All values must be unique")

        return options

    @model_validator(mode="after")
    def __validate_visible_options(self) -> "Self":
        if self.visible_options is None and self.options and len(self.options) >= self._MIN_VISIBLE_OPTIONS:
            self.visible_options = len(self.options)
        return self


class TextQuestionSettings(BaseModel):
    type: Literal["text"] = "text"

    use_markdown: bool = False
    use_table: bool = False


class TableQuestionSettings(BaseModel):
    type: Literal["table"] = "table"


QuestionSettings = Annotated[
    Union[
        LabelQuestionSettings,
        MultiLabelQuestionSettings,
        RankingQuestionSettings,
        RatingQuestionSettings,
        SpanQuestionSettings,
        TextQuestionSettings,
        TableQuestionSettings,
    ],
    Field(..., discriminator="type"),
]


class QuestionModel(ResourceModel):
    name: str
    settings: QuestionSettings

    title: str = Field(None, validate_default=True)
    description: Optional[str] = None
    required: bool = True

    dataset_id: Optional[UUID] = None

    @field_validator("title", mode="before")
    @classmethod
    def _title_default(cls, title, info: ValidationInfo):
        validated_title = title or info.data["name"]
        return validated_title

    @property
    def type(self) -> str:
        return self.settings.type

    @field_serializer("id", "dataset_id", when_used="unless-none")
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    model_config = ConfigDict(validate_assignment=True)
