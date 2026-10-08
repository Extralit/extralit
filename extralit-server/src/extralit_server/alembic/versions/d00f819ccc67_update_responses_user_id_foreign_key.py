"""update responses user_id foreign key

Revision ID: d00f819ccc67
Revises: 7552df94427a
Create Date: 2024-06-27 18:04:46.080762

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d00f819ccc67"
down_revision = "7552df94427a"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "responses_user_id_fkey"
NAMING_CONVENTION = {"fk": "%(table_name)s_%(column_0_name)s_fkey"}


def upgrade() -> None:
    op.execute("DELETE FROM responses WHERE user_id IS NULL")

    with op.batch_alter_table("responses", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="foreignkey")
        batch_op.create_foreign_key(CONSTRAINT_NAME, "users", ["user_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    with op.batch_alter_table("responses", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="foreignkey")
        batch_op.create_foreign_key(CONSTRAINT_NAME, "users", ["user_id"], ["id"], ondelete="SET NULL")
