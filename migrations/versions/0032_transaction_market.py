"""add market to transactions

Revision ID: 0032_transaction_market
Revises: 0031_entity_resolution
"""
from alembic import op
import sqlalchemy as sa
revision='0032_transaction_market'
down_revision='0031_entity_resolution'
branch_labels=None
depends_on=None

def upgrade():
    with op.batch_alter_table('transactions') as batch:
        batch.add_column(sa.Column('market_id', sa.Integer(), nullable=True))
        batch.create_index('ix_transactions_market_id', ['market_id'])
        batch.create_foreign_key('fk_transactions_market_id_markets', 'markets', ['market_id'], ['id'])

def downgrade():
    with op.batch_alter_table('transactions') as batch:
        batch.drop_constraint('fk_transactions_market_id_markets', type='foreignkey')
        batch.drop_index('ix_transactions_market_id')
        batch.drop_column('market_id')
