"""commercial intelligence
Revision ID: 0008_commercial_intelligence
Revises: 0007_rfq_communications
"""
from alembic import op
import sqlalchemy as sa
revision='0008_commercial_intelligence'
down_revision='0007_rfq_communications'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('supplier_quotes',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('manufacturer_id',sa.Integer(),sa.ForeignKey('manufacturers.id'),nullable=True),
        sa.Column('supplier_name',sa.String(250),nullable=False),
        sa.Column('currency',sa.String(10),nullable=False,server_default='USD'),
        sa.Column('unit_price',sa.Float(),nullable=False),sa.Column('quantity',sa.Float(),nullable=False),
        sa.Column('unit',sa.String(30),nullable=False,server_default='kg'),sa.Column('incoterm',sa.String(20),nullable=False,server_default='EXW'),
        sa.Column('freight_cost',sa.Float(),nullable=False,server_default='0'),sa.Column('other_cost',sa.Float(),nullable=False,server_default='0'),
        sa.Column('lead_time_days',sa.Integer(),nullable=True),sa.Column('validity_days',sa.Integer(),nullable=True),
        sa.Column('notes',sa.Text(),nullable=True),sa.Column('source_url',sa.Text(),nullable=True),sa.Column('status',sa.String(30),nullable=False,server_default='Unverified'),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for n,c in [('opportunity_id','opportunity_id'),('manufacturer_id','manufacturer_id'),('status','status')]: op.create_index('ix_supplier_quotes_'+n,'supplier_quotes',[c])
    op.create_table('commercial_offers',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('supplier_quote_id',sa.Integer(),sa.ForeignKey('supplier_quotes.id'),nullable=True),sa.Column('currency',sa.String(10),nullable=False,server_default='USD'),sa.Column('exchange_rate',sa.Float(),nullable=False,server_default='1'),
        sa.Column('quantity',sa.Float(),nullable=False),sa.Column('unit',sa.String(30),nullable=False,server_default='kg'),sa.Column('supplier_unit_price',sa.Float(),nullable=False,server_default='0'),
        sa.Column('packaging_cost',sa.Float(),nullable=False,server_default='0'),sa.Column('inland_cost',sa.Float(),nullable=False,server_default='0'),sa.Column('export_cost',sa.Float(),nullable=False,server_default='0'),sa.Column('freight_cost',sa.Float(),nullable=False,server_default='0'),sa.Column('insurance_cost',sa.Float(),nullable=False,server_default='0'),sa.Column('customs_cost',sa.Float(),nullable=False,server_default='0'),sa.Column('other_cost',sa.Float(),nullable=False,server_default='0'),
        sa.Column('commission_percent',sa.Float(),nullable=False,server_default='0'),sa.Column('commission_fixed',sa.Float(),nullable=False,server_default='0'),sa.Column('target_margin_percent',sa.Float(),nullable=False,server_default='10'),
        sa.Column('fob_total',sa.Float(),nullable=False,server_default='0'),sa.Column('cif_total',sa.Float(),nullable=False,server_default='0'),sa.Column('fob_unit_price',sa.Float(),nullable=False,server_default='0'),sa.Column('cif_unit_price',sa.Float(),nullable=False,server_default='0'),sa.Column('estimated_profit',sa.Float(),nullable=False,server_default='0'),sa.Column('estimated_profit_percent',sa.Float(),nullable=False,server_default='0'),
        sa.Column('status',sa.String(30),nullable=False,server_default='Draft'),sa.Column('notes',sa.Text(),nullable=True),sa.Column('assumptions',sa.JSON(),nullable=False,server_default='{}'),sa.Column('created_by',sa.Integer(),sa.ForeignKey('admins.id'),nullable=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for n,c in [('opportunity_id','opportunity_id'),('supplier_quote_id','supplier_quote_id'),('status','status'),('created_by','created_by')]: op.create_index('ix_commercial_offers_'+n,'commercial_offers',[c])

def downgrade():
    for n in ['created_by','status','supplier_quote_id','opportunity_id']: op.drop_index('ix_commercial_offers_'+n,table_name='commercial_offers')
    op.drop_table('commercial_offers')
    for n in ['status','manufacturer_id','opportunity_id']: op.drop_index('ix_supplier_quotes_'+n,table_name='supplier_quotes')
    op.drop_table('supplier_quotes')
