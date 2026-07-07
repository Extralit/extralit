"""create schema and schema_version tables

Revision ID: 9f3010c649c8
Revises: 54d65879a68e
Create Date: 2026-06-27 17:00:36.438902

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9f3010c649c8"
down_revision = "54d65879a68e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schemas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.Enum("singleton", "table", name="schema_kind_enum"), nullable=False),
        sa.Column("status", sa.Enum("draft", "published", name="schema_status_enum"), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name", name="schema_workspace_id_name_uq"),
    )
    op.create_index(op.f("ix_schemas_name"), "schemas", ["name"], unique=False)
    op.create_index(op.f("ix_schemas_status"), "schemas", ["status"], unique=False)
    op.create_index(op.f("ix_schemas_workspace_id"), "schemas", ["workspace_id"], unique=False)

    op.create_table(
        "schema_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("object_version_id", sa.Text(), nullable=True),
        sa.Column("etag", sa.String(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("parent_version_id", sa.Uuid(), nullable=True),
        sa.Column("columns_cache", sa.JSON(), nullable=False),
        sa.Column("review_widgets", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["schema_id"], ["schemas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_version_id"], ["schema_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schema_id", "version", name="schema_version_schema_id_version_uq"),
    )
    op.create_index(op.f("ix_schema_versions_schema_id"), "schema_versions", ["schema_id"], unique=False)
    op.create_index(op.f("ix_schema_versions_version"), "schema_versions", ["version"], unique=False)

    # Deferred FK: schemas.current_version_id -> schema_versions.id (created after both tables exist).
    # SQLite cannot ALTER-add a constraint; the column carries no DB-level FK there (model behaviour
    # is unaffected and the test suite runs on SQLite). Postgres gets the real constraint.
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "schema_current_version_id_fk",
            "schemas",
            "schema_versions",
            ["current_version_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("schema_current_version_id_fk", "schemas", type_="foreignkey")
    op.drop_index(op.f("ix_schema_versions_version"), table_name="schema_versions")
    op.drop_index(op.f("ix_schema_versions_schema_id"), table_name="schema_versions")
    op.drop_table("schema_versions")
    op.drop_index(op.f("ix_schemas_workspace_id"), table_name="schemas")
    op.drop_index(op.f("ix_schemas_status"), table_name="schemas")
    op.drop_index(op.f("ix_schemas_name"), table_name="schemas")
    op.drop_table("schemas")
    sa.Enum(name="schema_kind_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="schema_status_enum").drop(op.get_bind(), checkfirst=True)
