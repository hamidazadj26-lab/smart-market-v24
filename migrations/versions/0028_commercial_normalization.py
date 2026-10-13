"""commercial normalization metadata

Revision ID: 0028_commercial_normalization
Revises: 0027_source_discovery
"""
from alembic import op

revision='0028_commercial_normalization'
down_revision='0027_source_discovery'
branch_labels=None
depends_on=None

def upgrade():
    # Normalized commercial evidence is stored in SourceSignal.normalized_payload;
    # this migration intentionally has no schema change and marks the processing contract.
    pass

def downgrade():
    pass
