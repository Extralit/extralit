"""create workspaces table

Revision ID: 82a5a88a3fa5
Revises: 74694870197c
Create Date: 2023-02-13 18:00:04.369604

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "82a5a88a3fa5"
down_revision = "74694870197c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True, index=True),
        sa.Column("inserted_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workspaces")
