"""Add explicit source capability and runtime status fields.

Revision ID: 0026_source_capabilities
Revises: 0025_nullable_matching_dimensions
"""
from alembic import op
import sqlalchemy as sa

revision = '0026_source_capabilities'
down_revision = '0025_nullable_matching_dimensions'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sources') as batch:
        batch.add_column(sa.Column('access_mode', sa.String(length=40), nullable=False, server_default='manual'))
        batch.add_column(sa.Column('capability', sa.String(length=80), nullable=False, server_default='manual_entry'))
        batch.add_column(sa.Column('configured', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('authenticated', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('availability_status', sa.String(length=40), nullable=False, server_default='Unknown'))
        batch.add_column(sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('last_error', sa.Text(), nullable=True))
        batch.add_column(sa.Column('limitations', sa.JSON(), nullable=False, server_default='[]'))
        batch.create_index('ix_sources_access_mode', ['access_mode'])
        batch.create_index('ix_sources_capability', ['capability'])
        batch.create_index('ix_sources_configured', ['configured'])
        batch.create_index('ix_sources_authenticated', ['authenticated'])
        batch.create_index('ix_sources_availability_status', ['availability_status'])


def downgrade():
    with op.batch_alter_table('sources') as batch:
        batch.drop_index('ix_sources_availability_status')
        batch.drop_index('ix_sources_authenticated')
        batch.drop_index('ix_sources_configured')
        batch.drop_index('ix_sources_capability')
        batch.drop_index('ix_sources_access_mode')
        for name in ('limitations','last_error','last_success_at','last_checked_at','availability_status','authenticated','configured','capability','access_mode'):
            batch.drop_column(name)
