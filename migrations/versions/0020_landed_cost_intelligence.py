"""landed cost intelligence
Revision ID: 0020_landed_cost_intelligence
Revises: 0019_import_cost_intelligence
"""
from alembic import op
import sqlalchemy as sa
revision='0020_landed_cost_intelligence'; down_revision='0019_import_cost_intelligence'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('landed_cost_calculations',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=True),
        sa.Column('commercial_offer_id',sa.Integer(),sa.ForeignKey('commercial_offers.id'),nullable=True),
        sa.Column('logistics_scenario_id',sa.Integer(),sa.ForeignKey('logistics_scenarios.id'),nullable=True),
        sa.Column('import_cost_rule_id',sa.Integer(),sa.ForeignKey('import_cost_rules.id'),nullable=True),
        sa.Column('hs_code',sa.String(30),nullable=True), sa.Column('currency',sa.String(10),nullable=False),
        sa.Column('quantity',sa.Float(),nullable=False), sa.Column('unit',sa.String(30),nullable=False),
        sa.Column('supplier_cost',sa.Float(),nullable=False), sa.Column('packaging_cost',sa.Float(),nullable=False),
        sa.Column('inland_cost',sa.Float(),nullable=False), sa.Column('export_cost',sa.Float(),nullable=False),
        sa.Column('freight_cost',sa.Float(),nullable=False), sa.Column('insurance_cost',sa.Float(),nullable=False),
        sa.Column('customs_value',sa.Float(),nullable=False), sa.Column('import_taxes_and_fees',sa.Float(),nullable=False),
        sa.Column('destination_handling',sa.Float(),nullable=False), sa.Column('other_cost',sa.Float(),nullable=False),
        sa.Column('total_landed_cost',sa.Float(),nullable=False), sa.Column('landed_unit_cost',sa.Float(),nullable=False),
        sa.Column('fx_rate',sa.Float(),nullable=True), sa.Column('status',sa.String(30),nullable=False),
        sa.Column('assumptions',sa.JSON(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for n,c in [('ix_landed_cost_calculations_opportunity_id','opportunity_id'),('ix_landed_cost_calculations_commercial_offer_id','commercial_offer_id'),('ix_landed_cost_calculations_logistics_scenario_id','logistics_scenario_id'),('ix_landed_cost_calculations_import_cost_rule_id','import_cost_rule_id'),('ix_landed_cost_calculations_hs_code','hs_code')]: op.create_index(n,'landed_cost_calculations',[c])

def downgrade():
    op.drop_table('landed_cost_calculations')
