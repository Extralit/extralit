"""create workspaces_users table

Revision ID: 1769ee58fbb4
Revises: 82a5a88a3fa5
Create Date: 2023-02-14 10:36:56.313539

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1769ee58fbb4"
down_revision = "82a5a88a3fa5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces_users",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("inserted_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="workspace_id_user_id_uq"),
    )


def downgrade() -> None:
    op.drop_table("workspaces_users")
