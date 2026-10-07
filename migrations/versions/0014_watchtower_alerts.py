"""V22.7 Watchtower alerts.
Revision ID: 0014_watchtower_alerts
Revises: 0013_temporal_intelligence
"""
from alembic import op
import sqlalchemy as sa
revision='0014_watchtower_alerts'; down_revision='0013_temporal_intelligence'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('alert_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id'), nullable=False),
        sa.Column('alert_type', sa.String(80), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='New'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('dedup_key', sa.String(64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('admins.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    for n,c in [('ix_alert_events_opportunity_id','opportunity_id'),('ix_alert_events_alert_type','alert_type'),('ix_alert_events_severity','severity'),('ix_alert_events_status','status'),('ix_alert_events_dedup_key','dedup_key'),('ix_alert_events_first_seen_at','first_seen_at'),('ix_alert_events_last_seen_at','last_seen_at'),('ix_alert_events_created_by','created_by')]:
        op.create_index(n,'alert_events',[c])

def downgrade():
    for n in ['ix_alert_events_created_by','ix_alert_events_last_seen_at','ix_alert_events_first_seen_at','ix_alert_events_dedup_key','ix_alert_events_status','ix_alert_events_severity','ix_alert_events_alert_type','ix_alert_events_opportunity_id']:
        op.drop_index(n,table_name='alert_events')
    op.drop_table('alert_events')
