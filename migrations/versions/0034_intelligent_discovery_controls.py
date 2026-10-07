"""add centralized discovery usage controls

Revision ID: 0034_intelligent_discovery_controls
Revises: 0033_search_cache_jobs
"""
from alembic import op
import sqlalchemy as sa
revision='0034_intelligent_discovery_controls'; down_revision='0033_search_cache_jobs'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('discovery_usage',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('scope_type',sa.String(30),nullable=False),
        sa.Column('scope_key',sa.String(200),nullable=False),
        sa.Column('window_started_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('request_limit',sa.Integer(),nullable=False),
        sa.Column('requests_used',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
    )
    op.create_index('ux_discovery_usage_window','discovery_usage',['scope_type','scope_key','window_started_at'],unique=True)

def downgrade():
    op.drop_index('ux_discovery_usage_window',table_name='discovery_usage')
    op.drop_table('discovery_usage')
