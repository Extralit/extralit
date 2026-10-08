"""add metadata column to records table

Revision ID: 3ff6484f8b37
Revises: ae5522b4c674
Create Date: 2023-06-14 13:02:41.735153

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3ff6484f8b37"
down_revision = "ae5522b4c674"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("records", sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("records", "metadata")
