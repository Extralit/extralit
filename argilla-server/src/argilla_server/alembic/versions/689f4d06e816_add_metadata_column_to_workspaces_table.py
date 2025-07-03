"""add metadata column to workspaces table

Revision ID: 689f4d06e816
Revises: 580a6553186f
Create Date: 2025-07-03 01:43:49.549909

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '689f4d06e816'
down_revision = '580a6553186f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("workspaces", "metadata")
