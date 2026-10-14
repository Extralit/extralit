"""create webhooks table

Revision ID: 6ed1b8bf8e08
Revises: 660d6c6b3360
Create Date: 2024-09-02 11:41:57.561655

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6ed1b8bf8e08"
down_revision = "660d6c6b3360"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("webhooks")
