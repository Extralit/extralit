"""create users table

Revision ID: 74694870197c
Revises:
Create Date: 2023-02-13 17:08:05.445314

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "74694870197c"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("first_name", sa.String, nullable=False),
        sa.Column("last_name", sa.String),
        sa.Column("username", sa.String, nullable=False, unique=True, index=True),
        sa.Column("role", sa.String, nullable=False, index=True),
        sa.Column("api_key", sa.Text, nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("inserted_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("users")
