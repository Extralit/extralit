"""create v2_records table

Revision ID: 8136bc88ee3a
Revises: 9f3010c649c8
Create Date: 2026-07-03 18:07:04.507576

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8136bc88ee3a"
down_revision = "9f3010c649c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "completed", "discarded", name="v2_record_status_enum"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["schema_id"], ["schemas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schema_version_id"], ["schema_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schema_id", "external_id", name="v2_record_schema_id_external_id_uq"),
    )
    op.create_index(op.f("ix_v2_records_schema_id"), "v2_records", ["schema_id"], unique=False)
    op.create_index(op.f("ix_v2_records_reference"), "v2_records", ["reference"], unique=False)
    op.create_index(op.f("ix_v2_records_status"), "v2_records", ["status"], unique=False)
    op.create_index("ix_v2_records_schema_id_reference", "v2_records", ["schema_id", "reference"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_v2_records_schema_id_reference", table_name="v2_records")
    op.drop_index(op.f("ix_v2_records_status"), table_name="v2_records")
    op.drop_index(op.f("ix_v2_records_reference"), table_name="v2_records")
    op.drop_index(op.f("ix_v2_records_schema_id"), table_name="v2_records")
    op.drop_table("v2_records")
    sa.Enum(name="v2_record_status_enum").drop(op.get_bind(), checkfirst=True)
