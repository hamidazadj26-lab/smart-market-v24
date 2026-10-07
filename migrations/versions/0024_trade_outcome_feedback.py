"""structured closed-loop feedback from completed transactions"""
from alembic import op
import sqlalchemy as sa
revision='0024_trade_outcome_feedback'; down_revision='0023_transactions'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('trade_outcome_feedback',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('transaction_id',sa.Integer(),sa.ForeignKey('transactions.id'),nullable=False),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('product_id',sa.Integer(),sa.ForeignKey('products.id'),nullable=False),
        sa.Column('customer_id',sa.Integer(),sa.ForeignKey('customers.id'),nullable=True),
        sa.Column('manufacturer_id',sa.Integer(),sa.ForeignKey('manufacturers.id'),nullable=True),
        sa.Column('success_score',sa.Float(),nullable=True),
        sa.Column('actual_price_delta_pct',sa.Float(),nullable=True),
        sa.Column('actual_freight_delta_pct',sa.Float(),nullable=True),
        sa.Column('delivery_days',sa.Float(),nullable=True),
        sa.Column('quantity_variance_pct',sa.Float(),nullable=True),
        sa.Column('feedback',sa.JSON(),nullable=False),
        sa.Column('observed_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('created_by',sa.Integer(),sa.ForeignKey('admins.id'),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('transaction_id',name='uq_trade_outcome_feedback_transaction'))
    for name,col in [('ix_trade_outcome_feedback_transaction_id','transaction_id'),('ix_trade_outcome_feedback_opportunity_id','opportunity_id'),('ix_trade_outcome_feedback_product_id','product_id'),('ix_trade_outcome_feedback_customer_id','customer_id'),('ix_trade_outcome_feedback_manufacturer_id','manufacturer_id'),('ix_trade_outcome_feedback_observed_at','observed_at'),('ix_trade_outcome_feedback_created_by','created_by')]:
        op.create_index(name,'trade_outcome_feedback',[col])

def downgrade():
    op.drop_table('trade_outcome_feedback')
