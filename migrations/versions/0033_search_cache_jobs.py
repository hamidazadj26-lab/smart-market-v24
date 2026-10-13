"""add search cache and durable discovery jobs

Revision ID: 0033_search_cache_jobs
Revises: 0032_transaction_market
"""
from alembic import op
import sqlalchemy as sa
revision='0033_search_cache_jobs'; down_revision='0032_transaction_market'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('search_cache',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('cache_key',sa.String(64),nullable=False,unique=True,index=True),
        sa.Column('source',sa.String(80),nullable=False,index=True),
        sa.Column('query',sa.Text(),nullable=False),
        sa.Column('parameters',sa.JSON(),nullable=False),
        sa.Column('payload',sa.JSON(),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False,index=True),
        sa.Column('hit_count',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('last_hit_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
    )
    op.create_table('discovery_jobs',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('job_type',sa.String(50),nullable=False,index=True),
        sa.Column('status',sa.String(30),nullable=False,index=True),
        sa.Column('payload',sa.JSON(),nullable=False),
        sa.Column('result',sa.JSON(),nullable=False),
        sa.Column('error',sa.Text(),nullable=True),
        sa.Column('request_budget',sa.Integer(),nullable=False,server_default='50'),
        sa.Column('requests_used',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('max_retries',sa.Integer(),nullable=False,server_default='3'),
        sa.Column('retry_count',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('created_by',sa.Integer(),nullable=True),
        sa.Column('started_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('finished_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(['created_by'],['admins.id']),
    )
    op.create_index('ix_discovery_jobs_queue','discovery_jobs',['status'])

def downgrade():
    op.drop_index('ix_discovery_jobs_queue',table_name='discovery_jobs')
    op.drop_table('discovery_jobs'); op.drop_table('search_cache')
