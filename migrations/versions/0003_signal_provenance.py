"""add source signal provenance keys
Revision ID: 0003_signal_provenance
Revises: 0002_discovery_candidates
"""
from alembic import op
import sqlalchemy as sa
revision='0003_signal_provenance'; down_revision='0002_discovery_candidates'; branch_labels=None; depends_on=None
def upgrade():
    op.add_column('source_signals', sa.Column('content_hash', sa.String(64), nullable=True))
    op.add_column('source_signals', sa.Column('external_key', sa.String(500), nullable=True))
    op.create_index('ix_source_signals_content_hash','source_signals',['content_hash'])
    op.create_index('ix_source_signals_external_key','source_signals',['external_key'])
def downgrade():
    op.drop_index('ix_source_signals_external_key', table_name='source_signals')
    op.drop_index('ix_source_signals_content_hash', table_name='source_signals')
    op.drop_column('source_signals','external_key'); op.drop_column('source_signals','content_hash')
