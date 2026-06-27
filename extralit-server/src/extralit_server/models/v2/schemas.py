from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extralit_server.enums import SchemaKind, SchemaStatus
from extralit_server.models.base import DatabaseModel

SchemaKindEnum = SAEnum(SchemaKind, name="schema_kind_enum")
SchemaStatusEnum = SAEnum(SchemaStatus, name="schema_status_enum")


class Schema(DatabaseModel):
    __tablename__ = "schemas"

    name: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[SchemaKind] = mapped_column(SchemaKindEnum, default=SchemaKind.table)
    status: Mapped[SchemaStatus] = mapped_column(SchemaStatusEnum, default=SchemaStatus.draft, index=True)
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schema_versions.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    settings: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)

    versions: Mapped[list["SchemaVersion"]] = relationship(
        back_populates="schema",
        order_by="SchemaVersion.version",
        cascade="all, delete-orphan",
        foreign_keys="SchemaVersion.schema_id",
    )

    __table_args__ = (UniqueConstraint("workspace_id", "name", name="schema_workspace_id_name_uq"),)

    def __repr__(self) -> str:
        return f"Schema(id={self.id!s}, name={self.name!r}, kind={self.kind!r}, status={self.status!r})"


class SchemaVersion(DatabaseModel):
    __tablename__ = "schema_versions"

    schema_id: Mapped[UUID] = mapped_column(ForeignKey("schemas.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(index=True)
    object_key: Mapped[str] = mapped_column(Text)
    object_version_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    etag: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    parent_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schema_versions.id", ondelete="SET NULL"), nullable=True
    )
    columns_cache: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    # Out-of-band per-column review widgets (column name -> widget config); see spec §13.
    # Pandera's to_json drops Column.metadata, so this overlay is the source for columns_cache.review.
    review_widgets: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    schema: Mapped["Schema"] = relationship(back_populates="versions", foreign_keys=[schema_id])

    __table_args__ = (UniqueConstraint("schema_id", "version", name="schema_version_schema_id_version_uq"),)

    def __repr__(self) -> str:
        return f"SchemaVersion(id={self.id!s}, schema_id={self.schema_id!s}, version={self.version!r})"
