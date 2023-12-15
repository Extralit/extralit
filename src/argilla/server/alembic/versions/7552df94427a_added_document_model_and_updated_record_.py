"""Added Document model and updated Record model

Revision ID: 7552df94427a
Revises: bda6fe24314e
Create Date: 2023-11-02 13:54:59.615241

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '7552df94427a'
down_revision = 'bda6fe24314e'  # set to latest revision identifiers on updates from from argilla-io/argilla upstream repo.
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('documents',
    sa.Column('pmid', sa.String(), nullable=True),
    sa.Column('doi', sa.String(), nullable=True),
    sa.Column('file_name', sa.String(), nullable=False),
    sa.Column('file_data', sa.LargeBinary(), nullable=False),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column(
        "workspace_id", sa.Uuid, sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    ),
    sa.Column('inserted_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_pmid'), 'documents', ['pmid'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_pmid'), table_name='documents')
    op.drop_table('documents')
