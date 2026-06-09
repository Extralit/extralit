"""change suggestions score column to json

Revision ID: ca7293c38970
Revises: bda6fe24314e
Create Date: 2024-04-08 13:14:48.437677

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ca7293c38970"
down_revision = "bda6fe24314e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("suggestions") as batch_op:
        batch_op.alter_column("score", type_=sa.JSON(), postgresql_using="to_json(score)")

    op.execute(_score_update_statement())


def downgrade() -> None:
    op.add_column("suggestions", sa.Column("score_float", sa.Float(), nullable=True))
    op.execute(_score_float_update_statement())
    op.drop_column("suggestions", "score")
    op.alter_column("suggestions", "score_float", new_column_name="score")


def _score_update_statement() -> str:
    if op.get_context().dialect.name == "sqlite":
        return "UPDATE suggestions SET score = NULL WHERE json_type(value) = 'array'"
    elif op.get_context().dialect.name == "postgresql":
        return "UPDATE suggestions SET score = NULL WHERE json_typeof(value) = 'array'"
    else:
        raise NotImplementedError(f"Unsupported database: {op.get_context().dialect.name}")


def _score_float_update_statement() -> str:
    if op.get_context().dialect.name == "sqlite":
        return """
            UPDATE suggestions
            SET score_float =
                CASE
                    WHEN json_type(score) = 'real' THEN CAST(score AS FLOAT)
                    ELSE NULL
                END
        """
    elif op.get_context().dialect.name == "postgresql":
        return """
            UPDATE suggestions
            SET score_float =
                CASE
                    WHEN json_typeof(score) = 'number' THEN score::text::float
                    ELSE NULL
                END
        """
    else:
        raise NotImplementedError(f"Unsupported database: {op.get_context().dialect.name}")
