"""market price intelligence

Revision ID: 0010_market_price_intelligence
Revises: 0009_logistics_intelligence
"""
from alembic import op
import sqlalchemy as sa

revision='0010_market_price_intelligence'
down_revision='0009_logistics_intelligence'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('market_price_observations',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('product_id',sa.Integer(),nullable=False), sa.Column('market',sa.String(160),nullable=False), sa.Column('country',sa.String(100)), sa.Column('city',sa.String(120)), sa.Column('grade',sa.String(120)), sa.Column('specification',sa.JSON(),nullable=False),
        sa.Column('price',sa.Float(),nullable=False), sa.Column('currency',sa.String(10),nullable=False), sa.Column('unit',sa.String(30),nullable=False), sa.Column('incoterm',sa.String(20)), sa.Column('quantity',sa.Float()),
        sa.Column('source_id',sa.Integer()), sa.Column('source_url',sa.Text()), sa.Column('source_title',sa.String(300)), sa.Column('observed_at',sa.DateTime(timezone=True),nullable=False), sa.Column('verification_status',sa.String(30),nullable=False), sa.Column('confidence',sa.Float(),nullable=False), sa.Column('notes',sa.Text()),
        sa.ForeignKeyConstraint(['product_id'],['products.id']), sa.ForeignKeyConstraint(['source_id'],['sources.id']))
    for c in ['product_id','market','country','city','grade','currency','unit','incoterm','source_id','observed_at','verification_status']:
        op.create_index(f'ix_mpo_{c}', 'market_price_observations',[c])
    op.create_table('market_price_benchmarks',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('product_id',sa.Integer(),nullable=False), sa.Column('market',sa.String(160),nullable=False), sa.Column('country',sa.String(100)), sa.Column('grade',sa.String(120)), sa.Column('unit',sa.String(30),nullable=False), sa.Column('incoterm',sa.String(20)), sa.Column('currency',sa.String(10),nullable=False),
        sa.Column('observation_count',sa.Integer(),nullable=False), sa.Column('effective_count',sa.Integer(),nullable=False), sa.Column('low_price',sa.Float(),nullable=False), sa.Column('p25_price',sa.Float(),nullable=False), sa.Column('median_price',sa.Float(),nullable=False), sa.Column('p75_price',sa.Float(),nullable=False), sa.Column('high_price',sa.Float(),nullable=False), sa.Column('weighted_median_price',sa.Float(),nullable=False), sa.Column('confidence',sa.Float(),nullable=False), sa.Column('dispersion_pct',sa.Float(),nullable=False), sa.Column('benchmark_status',sa.String(30),nullable=False), sa.Column('as_of',sa.DateTime(timezone=True),nullable=False), sa.Column('assumptions',sa.JSON(),nullable=False),
        sa.ForeignKeyConstraint(['product_id'],['products.id']))
    for c in ['product_id','market','country','grade','unit','incoterm','as_of','benchmark_status']:
        op.create_index(f'ix_mpb_{c}', 'market_price_benchmarks',[c])

def downgrade():
    for c in ['product_id','market','country','grade','unit','incoterm','as_of','benchmark_status']:
        op.drop_index(f'ix_mpb_{c}',table_name='market_price_benchmarks')
    op.drop_table('market_price_benchmarks')
    for c in ['product_id','market','country','city','grade','currency','unit','incoterm','source_id','observed_at','verification_status']:
        op.drop_index(f'ix_mpo_{c}',table_name='market_price_observations')
    op.drop_table('market_price_observations')
