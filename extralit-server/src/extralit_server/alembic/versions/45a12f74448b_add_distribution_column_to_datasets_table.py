"""add distribution column to datasets table

Revision ID: 45a12f74448b
Revises: d00f819ccc67
Create Date: 2024-06-13 11:23:43.395093

"""

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "45a12f74448b"
down_revision = "d00f819ccc67"
branch_labels = None
depends_on = None

DISTRIBUTION_VALUE = json.dumps({"strategy": "overlap", "min_submitted": 1})


def upgrade() -> None:
    op.add_column("datasets", sa.Column("distribution", sa.JSON(), nullable=True))
    op.execute(f"UPDATE datasets SET distribution = '{DISTRIBUTION_VALUE}'")
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.alter_column("distribution", nullable=False)


def downgrade() -> None:
    op.drop_column("datasets", "distribution")
