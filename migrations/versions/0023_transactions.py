"""transaction lifecycle and closed-loop trade outcomes
Revision ID: 0023_transactions
Revises: 0022_trade_optimization
"""
from alembic import op
import sqlalchemy as sa
revision='0023_transactions'; down_revision='0022_trade_optimization'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('transactions',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('commercial_offer_id',sa.Integer(),sa.ForeignKey('commercial_offers.id'),nullable=True),
        sa.Column('customer_id',sa.Integer(),sa.ForeignKey('customers.id'),nullable=True),
        sa.Column('manufacturer_id',sa.Integer(),sa.ForeignKey('manufacturers.id'),nullable=True),
        sa.Column('product_id',sa.Integer(),sa.ForeignKey('products.id'),nullable=False),
        sa.Column('status',sa.String(40),nullable=False), sa.Column('currency',sa.String(10),nullable=False),
        sa.Column('quantity',sa.Float(),nullable=False), sa.Column('unit',sa.String(30),nullable=False),
        sa.Column('agreed_unit_price',sa.Float(),nullable=True), sa.Column('agreed_total',sa.Float(),nullable=True),
        sa.Column('incoterm',sa.String(20),nullable=True), sa.Column('payment_status',sa.String(30),nullable=False),
        sa.Column('logistics_status',sa.String(30),nullable=False),
        sa.Column('confirmed_at',sa.DateTime(timezone=True),nullable=True), sa.Column('paid_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('shipped_at',sa.DateTime(timezone=True),nullable=True), sa.Column('delivered_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('completed_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('actual_quantity',sa.Float(),nullable=True), sa.Column('actual_unit_price',sa.Float(),nullable=True),
        sa.Column('actual_total',sa.Float(),nullable=True), sa.Column('actual_freight',sa.Float(),nullable=True),
        sa.Column('actual_delivery_days',sa.Float(),nullable=True), sa.Column('outcome',sa.JSON(),nullable=False),
        sa.Column('notes',sa.Text(),nullable=True), sa.Column('created_by',sa.Integer(),sa.ForeignKey('admins.id'),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for name,col in [('ix_transactions_opportunity_id','opportunity_id'),('ix_transactions_commercial_offer_id','commercial_offer_id'),('ix_transactions_customer_id','customer_id'),('ix_transactions_manufacturer_id','manufacturer_id'),('ix_transactions_product_id','product_id'),('ix_transactions_status','status'),('ix_transactions_payment_status','payment_status'),('ix_transactions_logistics_status','logistics_status'),('ix_transactions_created_by','created_by')]: op.create_index(name,'transactions',[col])
    op.create_table('transaction_events',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('transaction_id',sa.Integer(),sa.ForeignKey('transactions.id'),nullable=False),
        sa.Column('event_type',sa.String(50),nullable=False), sa.Column('from_status',sa.String(40),nullable=True), sa.Column('to_status',sa.String(40),nullable=True),
        sa.Column('notes',sa.Text(),nullable=True), sa.Column('payload',sa.JSON(),nullable=False), sa.Column('created_by',sa.Integer(),sa.ForeignKey('admins.id'),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for name,col in [('ix_transaction_events_transaction_id','transaction_id'),('ix_transaction_events_event_type','event_type'),('ix_transaction_events_created_by','created_by')]: op.create_index(name,'transaction_events',[col])

def downgrade():
    op.drop_table('transaction_events'); op.drop_table('transactions')
