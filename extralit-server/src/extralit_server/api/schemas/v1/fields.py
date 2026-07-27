from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, constr
from pydantic import Field as PydanticField

from extralit_server.api.schemas.v1.commons import UpdateSchema
from extralit_server.enums import FieldType

FIELD_CREATE_NAME_MIN_LENGTH = 1
FIELD_CREATE_NAME_MAX_LENGTH = 200

FIELD_CREATE_TITLE_MIN_LENGTH = 1
FIELD_CREATE_TITLE_MAX_LENGTH = 500

FieldName = Annotated[
    constr(
        min_length=FIELD_CREATE_NAME_MIN_LENGTH,
        max_length=FIELD_CREATE_NAME_MAX_LENGTH,
    ),
    PydanticField(..., description="The name of the field"),
]

FieldTitle = Annotated[
    constr(
        min_length=FIELD_CREATE_TITLE_MIN_LENGTH,
        max_length=FIELD_CREATE_TITLE_MAX_LENGTH,
    ),
    PydanticField(..., description="The title of the field"),
]


class TextFieldSettings(BaseModel):
    type: Literal[FieldType.text]
    use_markdown: bool
    use_table: bool


class TextFieldSettingsCreate(BaseModel):
    type: Literal[FieldType.text]
    use_markdown: bool = False
    use_table: bool = False


class TextFieldSettingsUpdate(BaseModel):
    type: Literal[FieldType.text]
    use_markdown: bool
    use_table: bool


class ImageFieldSettings(BaseModel):
    type: Literal[FieldType.image]


class ImageFieldSettingsCreate(BaseModel):
    type: Literal[FieldType.image]


class ImageFieldSettingsUpdate(BaseModel):
    type: Literal[FieldType.image]


class ChatFieldSettings(BaseModel):
    type: Literal[FieldType.chat]
    use_markdown: bool


class ChatFieldSettingsCreate(BaseModel):
    type: Literal[FieldType.chat]
    use_markdown: bool = True


class ChatFieldSettingsUpdate(BaseModel):
    type: Literal[FieldType.chat]
    use_markdown: bool


class CustomFieldSettings(BaseModel):
    type: Literal[FieldType.custom]
    template: str
    advanced_mode: bool


class CustomFieldSettingsCreate(BaseModel):
    type: Literal[FieldType.custom]
    template: str
    advanced_mode: bool = False


class CustomFieldSettingsUpdate(BaseModel):
    type: Literal[FieldType.custom]
    template: str
    advanced_mode: bool


class TableFieldSettings(BaseModel):
    type: Literal[FieldType.table]


class TableFieldSettingsCreate(BaseModel):
    type: Literal[FieldType.table]


class TableFieldSettingsUpdate(BaseModel):
    type: Literal[FieldType.table]


class ColumnFieldSettings(BaseModel):
    type: Literal[FieldType.column]
    dtype: str
    nullable: bool = True
    # Opaque per-column review widget overlay, carried through to the client verbatim.
    # Replaces the former SchemaVersion.review_widgets column.
    review: dict[str, Any] | None = None


class ColumnFieldSettingsCreate(BaseModel):
    type: Literal[FieldType.column]
    dtype: str
    nullable: bool = True
    review: dict[str, Any] | None = None


class ColumnFieldSettingsUpdate(UpdateSchema):
    type: Literal[FieldType.column]
    dtype: str | None = None
    nullable: bool | None = None
    review: dict[str, Any] | None = None

    __non_nullable_fields__ = {"dtype"}


FieldSettings = Annotated[
    TextFieldSettings
    | ImageFieldSettings
    | ChatFieldSettings
    | CustomFieldSettings
    | TableFieldSettings
    | ColumnFieldSettings,
    PydanticField(..., discriminator="type"),
]

FieldSettingsCreate = Annotated[
    TextFieldSettingsCreate
    | ImageFieldSettingsCreate
    | ChatFieldSettingsCreate
    | CustomFieldSettingsCreate
    | TableFieldSettingsCreate
    | ColumnFieldSettingsCreate,
    PydanticField(..., discriminator="type"),
]

FieldSettingsUpdate = Annotated[
    TextFieldSettingsUpdate
    | ImageFieldSettingsUpdate
    | ChatFieldSettingsUpdate
    | CustomFieldSettingsUpdate
    | TableFieldSettingsUpdate
    | ColumnFieldSettingsUpdate,
    PydanticField(..., discriminator="type"),
]


class Field(BaseModel):
    id: UUID
    name: str
    title: str
    required: bool
    settings: FieldSettings
    dataset_id: UUID
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Fields(BaseModel):
    items: list[Field]


class FieldCreate(BaseModel):
    name: FieldName
    title: FieldTitle
    required: bool | None = None
    settings: FieldSettingsCreate


class FieldUpdate(UpdateSchema):
    title: FieldTitle | None = None
    settings: FieldSettingsUpdate | None = None

    __non_nullable_fields__ = {"title", "settings"}
