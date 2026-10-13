"""add discovery candidates

Revision ID: 0002_discovery_candidates
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision='0002_discovery_candidates'
down_revision='0001_initial'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        'discovery_candidates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_signal_id', sa.Integer(), sa.ForeignKey('source_signals.id'), nullable=True),
        sa.Column('name', sa.String(length=250), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=120), nullable=True),
        sa.Column('activity_type', sa.String(length=200), nullable=True),
        sa.Column('product_name', sa.String(length=200), nullable=True),
        sa.Column('candidate_type', sa.String(length=50), nullable=False, server_default='Potential Customer'),
        sa.Column('demand_likelihood', sa.Float(), nullable=False, server_default='0'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Review'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    for col in ('source_signal_id','name','country','city','product_name','candidate_type','status','is_archived'):
        op.create_index(f'ix_discovery_candidates_{col}', 'discovery_candidates', [col])

def downgrade():
    op.drop_table('discovery_candidates')
