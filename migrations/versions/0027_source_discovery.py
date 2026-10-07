"""Add bounded public source discovery metadata.

Revision ID: 0027_source_discovery
Revises: 0026_source_capabilities
"""
from alembic import op
import sqlalchemy as sa
revision='0027_source_discovery'
down_revision='0026_source_capabilities'
branch_labels=None
depends_on=None

def upgrade():
    with op.batch_alter_table('sources') as batch:
        batch.add_column(sa.Column('discovery_status', sa.String(length=40), nullable=True))
        batch.add_column(sa.Column('discovery_score', sa.Float(), nullable=True))
        batch.add_column(sa.Column('discovered_from_url', sa.Text(), nullable=True))
        batch.add_column(sa.Column('discovery_evidence', sa.JSON(), nullable=False, server_default='{}'))
        batch.create_index('ix_sources_discovery_status', ['discovery_status'])
        batch.create_index('ix_sources_discovery_score', ['discovery_score'])

def downgrade():
    with op.batch_alter_table('sources') as batch:
        batch.drop_index('ix_sources_discovery_score')
        batch.drop_index('ix_sources_discovery_status')
        for name in ('discovery_evidence','discovered_from_url','discovery_score','discovery_status'):
            batch.drop_column(name)
