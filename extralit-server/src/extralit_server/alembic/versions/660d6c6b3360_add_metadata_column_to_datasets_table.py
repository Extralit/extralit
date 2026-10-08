"""add metadata column to datasets table

Revision ID: 660d6c6b3360
Revises: 237f7c674d74
Create Date: 2024-10-04 16:47:21.611404

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "660d6c6b3360"
down_revision = "237f7c674d74"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("datasets", "metadata")
