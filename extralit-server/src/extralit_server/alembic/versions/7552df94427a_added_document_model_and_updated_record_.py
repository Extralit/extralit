# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""add Document model and update Record model

Revision ID: 7552df94427a
Revises: ca7293c38970
Create Date: 2023-11-02 13:54:59.615241

"""

import sqlalchemy as sa
from alembic import op

revision = "7552df94427a"
down_revision = "ca7293c38970"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("pmid", sa.String(), nullable=True),
        sa.Column("doi", sa.String(), nullable=True),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
        ),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_pmid"), "documents", ["pmid"], unique=False)
    op.create_index(op.f("ix_documents_reference"), "documents", ["reference"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_pmid"), table_name="documents")
    op.drop_index(op.f("ix_documents_reference"), table_name="documents")
    op.drop_table("documents")
