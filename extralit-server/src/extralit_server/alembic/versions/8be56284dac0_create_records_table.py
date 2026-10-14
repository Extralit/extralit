"""create records table

Revision ID: 8be56284dac0
Revises: 3a8e2f9b5dea
Create Date: 2023-04-13 12:56:56.456664

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8be56284dac0"
down_revision = "3a8e2f9b5dea"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "records",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("fields", sa.JSON, nullable=False),
        sa.Column("external_id", sa.String, index=True),
        sa.Column("dataset_id", sa.Uuid, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("inserted_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("external_id", "dataset_id", name="record_external_id_dataset_id_uq"),
    )


def downgrade() -> None:
    op.drop_table("records")
