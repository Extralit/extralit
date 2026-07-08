"""drop schemas.kind

Revision ID: 6393b1a01aa0
Revises: 8136bc88ee3a
Create Date: 2026-07-08 00:43:19.096246

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6393b1a01aa0"
down_revision = "8136bc88ee3a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("schemas", "kind")
    # `kind` is emergent from question/column bindings (spec §14), not a stored discriminator.
    sa.Enum(name="schema_kind_enum").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    schema_kind = sa.Enum("singleton", "table", name="schema_kind_enum")
    schema_kind.create(op.get_bind(), checkfirst=True)
    op.add_column("schemas", sa.Column("kind", schema_kind, nullable=False, server_default="table"))
    # The original column had no DB-level server_default (only a Python-side model default);
    # drop it post-backfill so downgrade restores the exact prior DDL.
    with op.batch_alter_table("schemas") as batch_op:
        batch_op.alter_column("kind", server_default=None)
