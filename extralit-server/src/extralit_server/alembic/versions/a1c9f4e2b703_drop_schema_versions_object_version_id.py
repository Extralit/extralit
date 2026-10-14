"""drop schema_versions.object_version_id

Revision ID: a1c9f4e2b703
Revises: 13da2d87e660
Create Date: 2026-08-18 09:00:00.000000

The column recorded the S3 native object version of a published schema body. It was
written best-effort and never read: a version's identity is `(dataset_id, version)`,
allocated under a row lock so every version lands on its own key, and its integrity is
`checksum`. Object-store versioning is being removed wholesale, so the column goes with it.
"""

import sqlalchemy as sa
from alembic import op

revision = "a1c9f4e2b703"
down_revision = "13da2d87e660"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("schema_versions") as batch_op:
        batch_op.drop_column("object_version_id")


def downgrade() -> None:
    with op.batch_alter_table("schema_versions") as batch_op:
        batch_op.add_column(sa.Column("object_version_id", sa.Text(), nullable=True))
