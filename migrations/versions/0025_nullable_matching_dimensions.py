"""Allow evidence-aware matching dimensions to remain unknown.

Revision ID: 0025_nullable_matching_dimensions
Revises: 0024_trade_outcome_feedback
"""
from alembic import op
import sqlalchemy as sa

revision = '0025_nullable_matching_dimensions'
down_revision = '0024_trade_outcome_feedback'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('opportunities') as batch:
        batch.alter_column('capacity_score', existing_type=sa.Float(), nullable=True)
        batch.alter_column('trust_score', existing_type=sa.Float(), nullable=True)
        batch.alter_column('location_score', existing_type=sa.Float(), nullable=True)


def downgrade():
    with op.batch_alter_table('opportunities') as batch:
        batch.alter_column('capacity_score', existing_type=sa.Float(), nullable=False)
        batch.alter_column('trust_score', existing_type=sa.Float(), nullable=False)
        batch.alter_column('location_score', existing_type=sa.Float(), nullable=False)
