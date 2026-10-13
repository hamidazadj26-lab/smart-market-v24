"""add opportunity action center
Revision ID: 0006_opportunity_actions
Revises: 0005_lead_ranking
"""
from alembic import op
import sqlalchemy as sa

revision='0006_opportunity_actions'
down_revision='0005_lead_ranking'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        'opportunity_actions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id'), nullable=False),
        sa.Column('action_type', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Planned'),
        sa.Column('subject', sa.String(length=250), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('channel', sa.String(length=40), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('admins.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_opportunity_actions_opportunity_id','opportunity_actions',['opportunity_id'])
    op.create_index('ix_opportunity_actions_status','opportunity_actions',['status'])
    op.create_index('ix_opportunity_actions_due_at','opportunity_actions',['due_at'])
    op.create_index('ix_opportunity_actions_created_by','opportunity_actions',['created_by'])

def downgrade():
    op.drop_index('ix_opportunity_actions_created_by', table_name='opportunity_actions')
    op.drop_index('ix_opportunity_actions_due_at', table_name='opportunity_actions')
    op.drop_index('ix_opportunity_actions_status', table_name='opportunity_actions')
    op.drop_index('ix_opportunity_actions_opportunity_id', table_name='opportunity_actions')
    op.drop_table('opportunity_actions')
