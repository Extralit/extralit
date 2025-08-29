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

"""create import_history table

Revision ID: 7d6b33203390
Revises: 580a6553186f
Create Date: 2025-07-17 22:45:24.899067

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7d6b33203390"
down_revision = "580a6553186f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_imports_user_id"), "imports", ["user_id"], unique=False)
    op.create_index(op.f("ix_imports_workspace_id"), "imports", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_documents_doi"), "documents", ["doi"], unique=False)
    op.add_column("documents", sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_doi"), table_name="documents")
    op.drop_index(op.f("ix_imports_workspace_id"), table_name="imports")
    op.drop_index(op.f("ix_imports_user_id"), table_name="imports")
    op.drop_table("imports")
    op.drop_column("documents", "metadata")
