from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extralit_server.enums import V2RecordStatus
from extralit_server.models.base import DatabaseModel

if TYPE_CHECKING:
    from extralit_server.models.v2.schemas import Schema, SchemaVersion

V2RecordStatusEnum = SAEnum(V2RecordStatus, name="v2_record_status_enum")


class V2Record(DatabaseModel):
    """v2 record: one typed row pinned to a schema version (spec §5).

    Table is `v2_records` because v1 owns `records`; the class is `V2Record` because a second
    declarative class named `Record` breaks v1's string-based `relationship("Record")` lookups.
    Both are renamed to the canonical names on v1 retirement (Phase 6).
    """

    __tablename__ = "v2_records"

    schema_id: Mapped[UUID] = mapped_column(ForeignKey("schemas.id", ondelete="CASCADE"), index=True)
    # CASCADE (not RESTRICT): versions are immutable and only deleted via the schema
    # cascade; RESTRICT could break the schemas-delete cascade on FK-check ordering.
    schema_version_id: Mapped[UUID] = mapped_column(ForeignKey("schema_versions.id", ondelete="CASCADE"))
    reference: Mapped[str] = mapped_column(String, index=True)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    fields: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    metadata_: Mapped[dict | None] = mapped_column("metadata", MutableDict.as_mutable(JSON), nullable=True)
    status: Mapped[V2RecordStatus] = mapped_column(
        V2RecordStatusEnum, default=V2RecordStatus.pending, server_default=V2RecordStatus.pending, index=True
    )

    # One-directional (Phase 1 convention): no Schema.records collection; DB-level CASCADE owns deletes.
    schema: Mapped["Schema"] = relationship("Schema")
    version: Mapped["SchemaVersion"] = relationship("SchemaVersion")

    __table_args__ = (
        UniqueConstraint("schema_id", "external_id", name="v2_record_schema_id_external_id_uq"),
        Index("ix_v2_records_schema_id_reference", "schema_id", "reference"),
    )

    def __repr__(self) -> str:
        return (
            f"V2Record(id={self.id!s}, schema_id={self.schema_id!s}, "
            f"reference={self.reference!r}, status={self.status!r})"
        )
