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

import base64
import secrets
from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import (
    JSON,
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    select,
    sql,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extralit_server.api.schemas.v1.questions import QuestionSettings
from extralit_server.enums import (
    DatasetDistributionStrategy,
    DatasetStatus,
    FieldType,
    MetadataPropertyType,
    QuestionType,
    RecordStatus,
    ResponseStatus,
    SuggestionType,
    UserRole,
)
from extralit_server.models.base import DatabaseModel
from extralit_server.models.metadata_properties import MetadataPropertySettings
from extralit_server.models.mixins import inserted_at_current_value

# Include here the data model ref to be accessible for automatic alembic migration scripts
__all__ = [
    "Dataset",
    "DatasetUser",
    "Document",
    "DocumentWorkflow",
    "Field",
    "ImportHistory",
    "MetadataProperty",
    "Question",
    "Record",
    "Response",
    "Suggestion",
    "User",
    "Vector",
    "VectorSettings",
    "Webhook",
    "Workspace",
    "WorkspaceUser",
]

_USER_API_KEY_BYTES_LENGTH = 80
_WEBHOOK_SECRET_BYTES_LENGTH = 64


class Field(DatabaseModel):
    __tablename__ = "fields"

    name: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(default=False)
    settings: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default={})
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="fields")

    __table_args__ = (UniqueConstraint("name", "dataset_id", name="field_name_dataset_id_uq"),)

    @property
    def is_text(self) -> bool:
        return self.settings.get("type") == FieldType.text

    @property
    def is_image(self) -> bool:
        return self.settings.get("type") == FieldType.image

    @property
    def is_chat(self) -> bool:
        return self.settings.get("type") == FieldType.chat

    @property
    def is_custom(self) -> bool:
        return self.settings.get("type") == FieldType.custom

    @property
    def is_table(self):
        return self.settings.get("type") == FieldType.table

    @property
    def type(self) -> FieldType:
        return FieldType(self.settings["type"])

    def __repr__(self):
        return (
            f"Field(id={str(self.id)!r}, name={self.name!r}, required={self.required!r}, "
            f"dataset_id={str(self.dataset_id)!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


ResponseStatusEnum = SAEnum(ResponseStatus, name="response_status_enum")


class Response(DatabaseModel):
    __tablename__ = "responses"

    values: Mapped[dict | None] = mapped_column(MutableDict.as_mutable(JSON))
    status: Mapped[ResponseStatus] = mapped_column(ResponseStatusEnum, default=ResponseStatus.submitted, index=True)
    record_id: Mapped[UUID] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    record: Mapped["Record"] = relationship(back_populates="responses")
    user: Mapped["User"] = relationship(back_populates="responses")

    __table_args__ = (UniqueConstraint("record_id", "user_id", name="response_record_id_user_id_uq"),)
    __upsertable_columns__ = {"values", "status"}

    @property
    def is_submitted(self) -> bool:
        return self.status == ResponseStatus.submitted

    def __repr__(self):
        return (
            f"Response(id={str(self.id)!r}, record_id={str(self.record_id)!r}, user_id={str(self.user_id)!r}, "
            f"status={self.status.value!r}, inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


SuggestionTypeEnum = SAEnum(SuggestionType, name="suggestion_type_enum")


class Suggestion(DatabaseModel):
    __tablename__ = "suggestions"

    value: Mapped[Any] = mapped_column(JSON)
    score: Mapped[float | list[float] | None] = mapped_column(JSON, nullable=True)
    agent: Mapped[str | None] = mapped_column(nullable=True)
    type: Mapped[SuggestionType | None] = mapped_column(SuggestionTypeEnum, nullable=True, index=True)
    record_id: Mapped[UUID] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)

    record: Mapped["Record"] = relationship(back_populates="suggestions")
    question: Mapped["Question"] = relationship(back_populates="suggestions")

    __table_args__ = (UniqueConstraint("record_id", "question_id", name="suggestion_record_id_question_id_uq"),)
    __upsertable_columns__ = {"value", "score", "agent", "type"}

    def __repr__(self) -> str:
        attrs = []
        for attr in ["id", "score", "agent", "type", "record_id", "question_id", "inserted_at", "updated_at", "value"]:
            value = getattr(self, attr)
            if value is not None:
                if attr == "value" and len(value) > 20:
                    value = value[:20] + "..."
                attrs.append(f"{attr}={value}")

        return f"Suggestion({', '.join(attrs)})"


class Vector(DatabaseModel):
    __tablename__ = "vectors"

    value: Mapped[list[Any]] = mapped_column(JSON)
    record_id: Mapped[UUID] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), index=True)
    vector_settings_id: Mapped[UUID] = mapped_column(ForeignKey("vectors_settings.id", ondelete="CASCADE"), index=True)

    record: Mapped["Record"] = relationship(back_populates="vectors")
    vector_settings: Mapped["VectorSettings"] = relationship(back_populates="vectors")

    __table_args__ = (
        UniqueConstraint("record_id", "vector_settings_id", name="vector_record_id_vector_settings_id_uq"),
    )
    __upsertable_columns__ = {"value"}

    def __repr__(self) -> str:
        return (
            f"Vector(id={self.id}, vector_settings_id={self.vector_settings_id}, record_id={self.record_id}, "
            f"inserted_at={self.inserted_at}, updated_at={self.updated_at})"
        )


class VectorSettings(DatabaseModel):
    __tablename__ = "vectors_settings"

    name: Mapped[str] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(Text)
    dimensions: Mapped[int] = mapped_column()
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="vectors_settings")
    vectors: Mapped[list["Vector"]] = relationship(
        back_populates="vector_settings",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Vector.inserted_at.asc(),
    )

    __table_args__ = (UniqueConstraint("name", "dataset_id", name="vector_settings_name_dataset_id_uq"),)

    def __repr__(self) -> str:
        return (
            f"VectorSettings(id={self.id}, name={self.name}, dimensions={self.dimensions}, "
            f"dataset_id={self.dataset_id}, inserted_at={self.inserted_at}, updated_at={self.updated_at})"
        )


RecordStatusEnum = SAEnum(RecordStatus, name="record_status_enum")


class Record(DatabaseModel):
    __tablename__ = "records"

    fields: Mapped[dict] = mapped_column(JSON, default={})
    metadata_: Mapped[dict | None] = mapped_column("metadata", MutableDict.as_mutable(JSON), nullable=True)
    status: Mapped[RecordStatus] = mapped_column(
        RecordStatusEnum, default=RecordStatus.pending, server_default=RecordStatus.pending, index=True
    )
    external_id: Mapped[str | None] = mapped_column(index=True)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="records")
    responses: Mapped[list["Response"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Response.inserted_at.asc(),
    )
    responses_submitted: Mapped[list["Response"]] = relationship(
        back_populates="record",
        viewonly=True,
        primaryjoin=f"and_(Record.id==Response.record_id, Response.status=='{ResponseStatus.submitted}')",
        order_by=Response.inserted_at.asc(),
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Suggestion.inserted_at.asc(),
    )
    vectors: Mapped[list["Vector"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Vector.inserted_at.asc(),
    )

    __table_args__ = (UniqueConstraint("external_id", "dataset_id", name="record_external_id_dataset_id_uq"),)

    def is_completed(self) -> bool:
        return self.status == RecordStatus.completed

    def vector_value_by_vector_settings(self, vector_settings: "VectorSettings") -> list[float] | None:
        for vector in self.vectors:
            if vector.vector_settings_id == vector_settings.id:
                return vector.value

    def __repr__(self):
        return (
            f"Record(id={str(self.id)!r}, external_id={self.external_id!r}, dataset_id={str(self.dataset_id)!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


class Question(DatabaseModel):
    __tablename__ = "questions"

    name: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    required: Mapped[bool] = mapped_column(default=False)
    settings: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default={})
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="questions")
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Suggestion.inserted_at.asc(),
    )

    __table_args__ = (UniqueConstraint("name", "dataset_id", name="question_name_dataset_id_uq"),)

    @property
    def parsed_settings(self) -> QuestionSettings:
        return TypeAdapter(QuestionSettings).validate_python(self.settings)

    @property
    def is_text(self) -> bool:
        return self.settings.get("type") == QuestionType.text

    @property
    def is_label_selection(self) -> bool:
        return self.settings.get("type") == QuestionType.label_selection

    @property
    def is_multi_label_selection(self) -> bool:
        return self.settings.get("type") == QuestionType.multi_label_selection

    @property
    def is_rating(self) -> bool:
        return self.settings.get("type") == QuestionType.rating

    @property
    def is_ranking(self) -> bool:
        return self.settings.get("type") == QuestionType.ranking

    @property
    def is_span(self) -> bool:
        return self.settings.get("type") == QuestionType.span

    @property
    def type(self) -> QuestionType:
        return QuestionType(self.settings["type"])

    @property
    def values(self) -> list[Any]:
        return [option["value"] for option in self.settings.get("options", [])]

    def __repr__(self):
        return (
            f"Question(id={str(self.id)!r}, name={self.name!r}, required={self.required!r}, "
            f"dataset_id={str(self.dataset_id)!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


class MetadataProperty(DatabaseModel):
    __tablename__ = "metadata_properties"

    name: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(Text)
    settings: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default={})
    allowed_roles: Mapped[list[UserRole]] = mapped_column(MutableList.as_mutable(JSON), default=[], server_default="[]")
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="metadata_properties")

    __table_args__ = (UniqueConstraint("name", "dataset_id", name="metadata_property_name_dataset_id_uq"),)

    @property
    def is_terms(self) -> bool:
        return self.settings.get("type") == MetadataPropertyType.terms

    @property
    def is_integer(self) -> bool:
        return self.settings.get("type") == MetadataPropertyType.integer

    @property
    def is_float(self) -> bool:
        return self.settings.get("type") == MetadataPropertyType.float

    @property
    def type(self) -> MetadataPropertyType:
        return MetadataPropertyType(self.settings["type"])

    @property
    def values(self) -> list[Any]:
        return self.settings.get("values", [])

    @property
    def parsed_settings(self) -> MetadataPropertySettings:
        return TypeAdapter(MetadataPropertySettings).validate_python(self.settings)

    @property
    def visible_for_annotators(self) -> bool:
        return UserRole.annotator in self.allowed_roles

    def __repr__(self):
        return (
            f"MetadataProperty(id={str(self.id)!r}, name={self.name!r}, dataset_id={str(self.dataset_id)!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


DatasetStatusEnum = SAEnum(DatasetStatus, name="dataset_status_enum")


def _updated_at_current_value(context: DefaultExecutionContext) -> datetime:
    return context.get_current_parameters(isolate_multiinsert_groups=False)["updated_at"]


class DatasetUser(DatabaseModel):
    __tablename__ = "datasets_users"
    __upsertable_columns__ = {}

    id = None  # This is a workaround to avoid the id column in the table

    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    dataset: Mapped["Dataset"] = relationship(viewonly=True)
    user: Mapped["User"] = relationship(viewonly=True)

    __table_args__ = (PrimaryKeyConstraint("dataset_id", "user_id"),)

    def __repr__(self):
        return (
            f"DatasetUser(id={str(self.id)!r}, dataset_id={str(self.dataset_id)!r}, "
            f"user_id={str(self.user_id)!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


class Dataset(DatabaseModel):
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(index=True)
    guidelines: Mapped[str | None] = mapped_column(Text)
    allow_extra_metadata: Mapped[bool] = mapped_column(default=True, server_default=sql.true())
    status: Mapped[DatasetStatus] = mapped_column(DatasetStatusEnum, default=DatasetStatus.draft, index=True)
    distribution: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    inserted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=inserted_at_current_value, onupdate=datetime.utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(
        default=inserted_at_current_value, onupdate=_updated_at_current_value
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="datasets")
    fields: Mapped[list["Field"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Field.inserted_at.asc(),
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Question.inserted_at.asc(),
    )
    records: Mapped[list["Record"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Record.inserted_at.asc(),
    )
    metadata_properties: Mapped[list["MetadataProperty"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=MetadataProperty.inserted_at.asc(),
    )
    vectors_settings: Mapped[list["VectorSettings"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=VectorSettings.inserted_at.asc(),
    )

    users: Mapped[list["User"]] = relationship(
        secondary="datasets_users",
        back_populates="datasets",
        passive_deletes=True,
        order_by=DatasetUser.inserted_at.asc(),
    )

    __table_args__ = (UniqueConstraint("name", "workspace_id", name="dataset_name_workspace_id_uq"),)

    @property
    def is_draft(self) -> bool:
        return self.status == DatasetStatus.draft

    @property
    def is_ready(self) -> bool:
        return self.status == DatasetStatus.ready

    @property
    def distribution_strategy(self) -> DatasetDistributionStrategy:
        return DatasetDistributionStrategy(self.distribution["strategy"])

    def field_by_name(self, name: str) -> Union["Field", None]:
        for field in self.fields:
            if field.name == name:
                return field

    def metadata_property_by_name(self, name: str) -> Union["MetadataProperty", None]:
        for metadata_property in self.metadata_properties:
            if metadata_property.name == name:
                return metadata_property

    def question_by_id(self, question_id: UUID) -> Question | None:
        for question in self.questions:
            if question.id == question_id:
                return question

    def question_by_name(self, name: str) -> Question | None:
        for question in self.questions:
            if question.name == name:
                return question

    def vector_settings_by_name(self, name: str) -> Union["VectorSettings", None]:
        for vector_settings in self.vectors_settings:
            if vector_settings.name == name:
                return vector_settings

    def __repr__(self):
        return (
            f"Dataset(id={str(self.id)!r}, name={self.name!r}, guidelines={self.guidelines!r}, "
            f"status={self.status.value!r}, workspace_id={str(self.workspace_id)!r}, "
            f"last_activity_at={str(self.last_activity_at)!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


class WorkspaceUser(DatabaseModel):
    __tablename__ = "workspaces_users"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    workspace: Mapped["Workspace"] = relationship(viewonly=True)
    user: Mapped["User"] = relationship(viewonly=True)

    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="workspace_id_user_id_uq"),)

    def __repr__(self):
        return (
            f"WorkspaceUser(id={str(self.id)!r}, workspace_id={str(self.workspace_id)!r}, "
            f"user_id={str(self.user_id)!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


class Workspace(DatabaseModel):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(unique=True, index=True)

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="workspace", order_by=Dataset.inserted_at.asc())
    users: Mapped[list["User"]] = relationship(
        secondary="workspaces_users", back_populates="workspaces", order_by=WorkspaceUser.inserted_at.asc()
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return (
            f"Workspace(id={str(self.id)!r}, name={self.name!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


def generate_user_api_key() -> str:
    return secrets.token_urlsafe(_USER_API_KEY_BYTES_LENGTH)


UserRoleEnum = SAEnum(UserRole, name="user_role_enum")


class User(DatabaseModel):
    __tablename__ = "users"

    first_name: Mapped[str]
    last_name: Mapped[str | None]
    username: Mapped[str] = mapped_column(unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(UserRoleEnum, default=UserRole.annotator, index=True)
    api_key: Mapped[str] = mapped_column(Text, unique=True, index=True, default=generate_user_api_key)
    password_hash: Mapped[str] = mapped_column(Text)

    workspaces: Mapped[list["Workspace"]] = relationship(
        secondary="workspaces_users", back_populates="users", order_by=WorkspaceUser.inserted_at.asc()
    )
    responses: Mapped[list["Response"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Response.inserted_at.asc(),
    )

    datasets: Mapped[list["Dataset"]] = relationship(
        secondary="datasets_users",
        back_populates="users",
        order_by=DatasetUser.inserted_at.asc(),
    )

    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.owner

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin

    @property
    def is_annotator(self) -> bool:
        return self.role == UserRole.annotator

    async def is_member(self, workspace_id: UUID) -> bool:
        # TODO: Change query to use exists may improve performance
        return (
            await WorkspaceUser.get_by(self.current_async_session, workspace_id=workspace_id, user_id=self.id)
            is not None
        )

    async def is_member_of_workspace_name(self, workspace_name: str) -> bool:
        workspace = await Workspace.get_by(self.current_async_session, name=workspace_name)
        if not workspace:
            return False
        return (
            await WorkspaceUser.get_by(self.current_async_session, workspace_id=workspace.id, user_id=self.id)
            is not None
        )

    def __repr__(self):
        return (
            f"User(id={str(self.id)!r}, first_name={self.first_name!r}, last_name={self.last_name!r}, "
            f"username={self.username!r}, role={self.role.value!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


class Document(DatabaseModel):
    __tablename__ = "documents"

    url: Mapped[str] = mapped_column(String, nullable=True)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    reference: Mapped[str] = mapped_column(String, index=True, nullable=True)
    pmid: Mapped[str] = mapped_column(String, index=True, nullable=True)
    doi: Mapped[str] = mapped_column(String, index=True, nullable=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", MutableDict.as_mutable(JSON()), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="documents")
    workflows: Mapped[list["DocumentWorkflow"]] = relationship(
        "DocumentWorkflow",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentWorkflow.inserted_at.desc()",
    )

    def __repr__(self):
        return (
            f"Document(id={str(self.id)!r}, workspace_id={str(self.workspace_id)!r}, reference={self.reference!r},"
            f"pmid={self.pmid!r}, doi={self.doi!r}, file_name={self.file_name!r}, url={self.url!r})"
        )


def generate_webhook_secret() -> str:
    # NOTE: https://www.standardwebhooks.com implementation requires a base64 encoded secret
    return base64.b64encode(secrets.token_bytes(_WEBHOOK_SECRET_BYTES_LENGTH)).decode("utf-8")


class Webhook(DatabaseModel):
    __tablename__ = "webhooks"

    url: Mapped[str] = mapped_column(Text)
    secret: Mapped[str] = mapped_column(Text, default=generate_webhook_secret)
    events: Mapped[list[str]] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(default=True, server_default=sql.true())
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return (
            f"Webhook(id={str(self.id)!r}, url={self.url!r}, events={self.events!r}, "
            f"enabled={self.enabled!r}, description={self.description!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


class ImportHistory(DatabaseModel):
    __tablename__ = "imports"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON()), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", MutableDict.as_mutable(JSON()), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return (
            f"ImportHistory(id={str(self.id)!r}, workspace_id={str(self.workspace_id)!r}, "
            f"user_id={str(self.user_id)!r}, filename={self.filename!r}, "
            f"inserted_at={str(self.inserted_at)!r}, updated_at={str(self.updated_at)!r})"
        )


class DocumentWorkflow(DatabaseModel):
    """Track document processing workflows for efficient job querying."""

    __tablename__ = "workflows"

    workflow_type: Mapped[str] = mapped_column(String(50))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    # RQ Group integration
    group_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)  # Cached workflow status

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="workflows")
    workspace: Mapped["Workspace"] = relationship("Workspace")

    @classmethod
    async def get_by_document_id(cls, db: AsyncSession, document_id: UUID) -> Optional["DocumentWorkflow"]:
        """Get workflow by document ID."""
        result = await db.execute(select(cls).where(cls.document_id == document_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_group_id(cls, db: AsyncSession, group_id: str) -> Optional["DocumentWorkflow"]:
        """Get workflow by RQ Group ID."""
        result = await db.execute(select(cls).where(cls.group_id == group_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_reference(
        cls, db: AsyncSession, reference: str, workspace_id: str | None = None
    ) -> list["DocumentWorkflow"]:
        """Get workflows by reference (batch tracking)."""
        query = select(cls).where(cls.reference == reference)
        if workspace_id:
            query = query.where(cls.workspace_id == workspace_id)
        result = await db.execute(query)
        return result.scalars().all()
