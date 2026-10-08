"""create fields table

Revision ID: ae5522b4c674
Revises: e402e9d9245e
Create Date: 2023-04-21 16:10:27.320399

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import expression

# revision identifiers, used by Alembic.
revision = "ae5522b4c674"
down_revision = "e402e9d9245e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fields",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("name", sa.String, nullable=False, index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("required", sa.Boolean, nullable=False, server_default=expression.false()),
        sa.Column("settings", sa.JSON, nullable=False),
        sa.Column("dataset_id", sa.Uuid, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("inserted_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("name", "dataset_id", name="field_name_dataset_id_uq"),
    )


def downgrade() -> None:
    op.drop_table("fields")
