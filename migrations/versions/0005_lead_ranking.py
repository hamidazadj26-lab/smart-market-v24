"""lead ranking baseline
Revision ID: 0005_lead_ranking
Revises: 0004_verification_intelligence
"""
from alembic import op
revision='0005_lead_ranking'; down_revision='0004_verification_intelligence'; branch_labels=None; depends_on=None
def upgrade():
    # V20.7 ranking is computed from existing Opportunity fields; no schema change is required.
    pass
def downgrade():
    pass
