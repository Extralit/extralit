"""add allow_extra_metadata column to datasets table

Revision ID: b8458008b60e
Revises: 7cbcccf8b57a
Create Date: 2023-09-29 13:51:44.525944

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8458008b60e"
down_revision = "7cbcccf8b57a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "datasets", sa.Column("allow_extra_metadata", sa.Boolean(), server_default=sa.text("true"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("datasets", "allow_extra_metadata")
