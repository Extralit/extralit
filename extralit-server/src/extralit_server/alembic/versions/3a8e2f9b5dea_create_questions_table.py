"""create questions table

Revision ID: 3a8e2f9b5dea
Revises: b9099dc08489
Create Date: 2023-04-03 17:24:53.836750

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import expression

# revision identifiers, used by Alembic.
revision = "3a8e2f9b5dea"
down_revision = "b9099dc08489"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("name", sa.String, nullable=False, index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("required", sa.Boolean, nullable=False, server_default=expression.false()),
        sa.Column("settings", sa.JSON, nullable=False),
        sa.Column("dataset_id", sa.Uuid, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("inserted_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("name", "dataset_id", name="question_name_dataset_id_uq"),
    )


def downgrade() -> None:
    op.drop_table("questions")
