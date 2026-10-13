"""end-to-end trade cost and route optimizer
Revision ID: 0022_trade_optimization
Revises: 0021_trade_route_intelligence
"""
from alembic import op
import sqlalchemy as sa
revision='0022_trade_optimization'; down_revision='0021_trade_route_intelligence'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('trade_optimization_runs',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('quantity',sa.Float(),nullable=False),
        sa.Column('target_currency',sa.String(10),nullable=False),
        sa.Column('status',sa.String(30),nullable=False),
        sa.Column('scenario_count',sa.Integer(),nullable=False),
        sa.Column('assumptions',sa.JSON(),nullable=False),
        sa.Column('created_by',sa.Integer(),sa.ForeignKey('admins.id'),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_trade_optimization_runs_opportunity_id','trade_optimization_runs',['opportunity_id'])
    op.create_index('ix_trade_optimization_runs_status','trade_optimization_runs',['status'])
    op.create_table('trade_optimization_results',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('run_id',sa.Integer(),sa.ForeignKey('trade_optimization_runs.id'),nullable=False),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('supplier_quote_id',sa.Integer(),sa.ForeignKey('supplier_quotes.id'),nullable=False),
        sa.Column('route_id',sa.Integer(),sa.ForeignKey('trade_route_profiles.id'),nullable=False),
        sa.Column('target_currency',sa.String(10),nullable=False),
        sa.Column('quantity',sa.Float(),nullable=False),
        sa.Column('supplier_goods_total',sa.Float(),nullable=False),
        sa.Column('supplier_other_cost',sa.Float(),nullable=False),
        sa.Column('route_cost',sa.Float(),nullable=False),
        sa.Column('import_taxes_and_fees',sa.Float(),nullable=False),
        sa.Column('total_trade_cost',sa.Float(),nullable=False),
        sa.Column('trade_unit_cost',sa.Float(),nullable=False),
        sa.Column('route_distance_km',sa.Float(),nullable=False),
        sa.Column('route_transit_days',sa.Float(),nullable=False),
        sa.Column('rank',sa.Integer(),nullable=False),
        sa.Column('assumptions',sa.JSON(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for name, table, cols in [
        ('ix_trade_optimization_results_run_id','trade_optimization_results',['run_id']),
        ('ix_trade_optimization_results_opportunity_id','trade_optimization_results',['opportunity_id']),
        ('ix_trade_optimization_results_supplier_quote_id','trade_optimization_results',['supplier_quote_id']),
        ('ix_trade_optimization_results_route_id','trade_optimization_results',['route_id']),
        ('ix_trade_optimization_results_rank','trade_optimization_results',['rank'])]: op.create_index(name,table,cols)

def downgrade():
    op.drop_table('trade_optimization_results'); op.drop_table('trade_optimization_runs')
