"""fix suggestions type enum values

Revision ID: 1e629a913727
Revises: 3fc3c0839959
Create Date: 2023-07-24 12:47:11.715011

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "1e629a913727"
down_revision = "3fc3c0839959"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE suggestion_type_enum ADD VALUE IF NOT EXISTS 'model';")
        op.execute("ALTER TYPE suggestion_type_enum ADD VALUE IF NOT EXISTS 'human';")


def downgrade() -> None:
    pass
