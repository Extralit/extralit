"""create responses table

Revision ID: e402e9d9245e
Revises: 8be56284dac0
Create Date: 2023-04-13 14:48:52.462570

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e402e9d9245e"
down_revision = "8be56284dac0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "responses",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("values", sa.JSON),
        sa.Column("status", sa.String, nullable=False, index=True),
        sa.Column("record_id", sa.Uuid, sa.ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("inserted_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("record_id", "user_id", name="response_record_id_user_id_uq"),
    )


def downgrade() -> None:
    op.drop_table("responses")
