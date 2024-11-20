"""Add FieldType.table and update fields with use_table=True

Revision ID: 2c12e273a93e
Revises: 660d6c6b3360
Create Date: 2024-11-19 17:55:43.983366

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2c12e273a93e'
down_revision = '660d6c6b3360'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    fields_table = sa.Table(
        'fields',
        sa.MetaData(),
        sa.Column('id', sa.String),
        sa.Column('settings', postgresql.JSONB),
    )

    # Update 'type' in settings to 'table' where it's 'text' and 'use_table' is True
    fields = connection.execute(
        sa.select([fields_table.c.id, fields_table.c.settings])
        .where(
            sa.and_(
                fields_table.c.settings['type'].astext == 'text',
                fields_table.c.settings['use_table'].astext == 'true'
            )
        )
    ).fetchall()

    for field_id, settings in fields:
        settings['type'] = 'table'
        connection.execute(
            fields_table.update()
            .where(fields_table.c.id == field_id)
            .values(settings=settings)
        )

def downgrade():
    # Revert 'type' back to 'text' where it's 'table'
    connection = op.get_bind()
    fields_table = sa.Table(
        'fields',
        sa.MetaData(),
        sa.Column('id', sa.String),
        sa.Column('settings', postgresql.JSONB),
    )

    fields = connection.execute(
        sa.select([fields_table.c.id, fields_table.c.settings])
        .where(fields_table.c.settings['type'].astext == 'table')
    ).fetchall()

    for field_id, settings in fields:
        settings['type'] = 'text'
        connection.execute(
            fields_table.update()
            .where(fields_table.c.id == field_id)
            .values(settings=settings)
        )
