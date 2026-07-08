"""create v2 annotation tables

Revision ID: c1510e93882a
Revises: 6393b1a01aa0
Create Date: 2026-07-08 01:04:40.245236

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1510e93882a"
down_revision = "6393b1a01aa0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "text",
                "rating",
                "label_selection",
                "multi_label_selection",
                "ranking",
                "span",
                "table",
                name="v2_question_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["schema_id"], ["schemas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schema_id", "name", name="v2_question_schema_id_name_uq"),
    )
    op.create_index(op.f("ix_v2_questions_schema_id"), "v2_questions", ["schema_id"], unique=False)
    op.create_index(op.f("ix_v2_questions_name"), "v2_questions", ["name"], unique=False)
    op.create_index(op.f("ix_v2_questions_type"), "v2_questions", ["type"], unique=False)

    op.create_table(
        "v2_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("score", sa.JSON(), nullable=True),
        sa.Column("agent", sa.String(), nullable=True),
        sa.Column(
            "type",
            sa.Enum("model", "human", "selection", name="v2_suggestion_type_enum"),
            nullable=True,
        ),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["record_id"], ["v2_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["v2_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", "question_id", name="v2_suggestion_record_id_question_id_uq"),
    )
    op.create_index(op.f("ix_v2_suggestions_record_id"), "v2_suggestions", ["record_id"], unique=False)
    op.create_index(op.f("ix_v2_suggestions_question_id"), "v2_suggestions", ["question_id"], unique=False)
    op.create_index(op.f("ix_v2_suggestions_type"), "v2_suggestions", ["type"], unique=False)

    op.create_table(
        "v2_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("values", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "submitted", "discarded", name="v2_response_status_enum"),
            nullable=False,
        ),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["record_id"], ["v2_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", "user_id", name="v2_response_record_id_user_id_uq"),
    )
    op.create_index(op.f("ix_v2_responses_record_id"), "v2_responses", ["record_id"], unique=False)
    op.create_index(op.f("ix_v2_responses_user_id"), "v2_responses", ["user_id"], unique=False)
    op.create_index(op.f("ix_v2_responses_status"), "v2_responses", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_v2_responses_status"), table_name="v2_responses")
    op.drop_index(op.f("ix_v2_responses_user_id"), table_name="v2_responses")
    op.drop_index(op.f("ix_v2_responses_record_id"), table_name="v2_responses")
    op.drop_table("v2_responses")

    op.drop_index(op.f("ix_v2_suggestions_type"), table_name="v2_suggestions")
    op.drop_index(op.f("ix_v2_suggestions_question_id"), table_name="v2_suggestions")
    op.drop_index(op.f("ix_v2_suggestions_record_id"), table_name="v2_suggestions")
    op.drop_table("v2_suggestions")

    op.drop_index(op.f("ix_v2_questions_type"), table_name="v2_questions")
    op.drop_index(op.f("ix_v2_questions_name"), table_name="v2_questions")
    op.drop_index(op.f("ix_v2_questions_schema_id"), table_name="v2_questions")
    op.drop_table("v2_questions")

    sa.Enum(name="v2_response_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="v2_suggestion_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="v2_question_type_enum").drop(op.get_bind(), checkfirst=True)
