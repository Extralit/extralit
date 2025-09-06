"""add metadata column to questions table

Revision ID: 8d14c54ca8e1
Revises: 54d65879a68e
Create Date: 2025-09-06 09:02:48.874255

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d14c54ca8e1'
down_revision = '54d65879a68e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add metadata column to questions table
    op.add_column('questions', sa.Column('metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Drop metadata column from questions table
    op.drop_column('questions', 'metadata')
