from typing import Annotated, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator
from pydantic_core.core_schema import ValidationInfo

from extralit._helpers import log_message
from extralit._models import ResourceModel


class TextFieldSettings(BaseModel):
    type: Literal["text"] = "text"
    use_markdown: Optional[bool] = False
    use_table: Optional[bool] = False


class ImageFieldSettings(BaseModel):
    type: Literal["image"] = "image"


class ChatFieldSettings(BaseModel):
    type: Literal["chat"] = "chat"
    use_markdown: Optional[bool] = True


class CustomFieldSettings(BaseModel):
    type: Literal["custom"] = "custom"
    template: str
    advanced_mode: Optional[bool] = False


class TableFieldSettings(BaseModel):
    type: Literal["table"] = "table"


FieldSettings = Annotated[
    Union[TextFieldSettings, ImageFieldSettings, ChatFieldSettings, CustomFieldSettings, TableFieldSettings],
    Field(..., discriminator="type"),
]


class FieldModel(ResourceModel):
    name: str
    settings: FieldSettings
    title: Optional[str] = None
    required: bool = True
    description: Optional[str] = None
    dataset_id: Optional[UUID] = None

    @field_validator("title")
    @classmethod
    def __title_default(cls, title: str, info: ValidationInfo) -> str:
        data = info.data
        validated_title = title or data["name"]
        log_message(f"TextField title is {validated_title}")
        return validated_title

    @field_serializer("id", "dataset_id", when_used="unless-none")
    def serialize_id(self, value: UUID) -> str:
        return str(value)
