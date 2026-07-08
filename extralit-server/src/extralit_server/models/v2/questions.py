from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extralit_server.enums import QuestionType
from extralit_server.models.base import DatabaseModel

if TYPE_CHECKING:
    from extralit_server.models.v2.schemas import Schema

# Distinct PG enum name (v1 stores question type inside settings JSON, but v2 promotes it to a
# first-class column). Reuses the v1 QuestionType *values*.
V2QuestionTypeEnum = SAEnum(QuestionType, name="v2_question_type_enum")


class V2Question(DatabaseModel):
    """Reviewable column binding + review config (spec §17). Its settings drive per-cell
    value validation. `columns` binds >=1 schema column (exactly 1 for non-table types)."""

    __tablename__ = "v2_questions"

    schema_id: Mapped[UUID] = mapped_column(ForeignKey("schemas.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[QuestionType] = mapped_column(V2QuestionTypeEnum, index=True)
    columns: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    settings: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    required: Mapped[bool] = mapped_column(default=False)

    schema: Mapped["Schema"] = relationship("Schema")

    __table_args__ = (UniqueConstraint("schema_id", "name", name="v2_question_schema_id_name_uq"),)

    def __repr__(self) -> str:
        return f"V2Question(id={self.id!s}, schema_id={self.schema_id!s}, name={self.name!r}, type={self.type!r})"
