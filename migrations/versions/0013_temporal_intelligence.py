"""V22.5 temporal intelligence indexes.
Revision ID: 0013_temporal_intelligence
Revises: 0012_automation_followups
"""
from alembic import op
import sqlalchemy as sa
revision='0013_temporal_intelligence'; down_revision='0012_automation_followups'; branch_labels=None; depends_on=None

def upgrade():
    op.create_index('ix_market_price_obs_product_market_observed','market_price_observations',['product_id','market','observed_at'])
    op.create_index('ix_opportunities_stage_updated','opportunities',['opportunity_stage','stage_updated_at'])

def downgrade():
    op.drop_index('ix_opportunities_stage_updated',table_name='opportunities')
    op.drop_index('ix_market_price_obs_product_market_observed',table_name='market_price_observations')
