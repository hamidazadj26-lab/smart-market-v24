"""logistics intelligence
Revision ID: 0009_logistics_intelligence
Revises: 0008_commercial_intelligence
"""
from alembic import op
import sqlalchemy as sa
revision='0009_logistics_intelligence'; down_revision='0008_commercial_intelligence'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('logistics_scenarios',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('name',sa.String(200),nullable=False), sa.Column('origin',sa.String(250),nullable=False), sa.Column('destination',sa.String(250),nullable=False),
        sa.Column('transport_mode',sa.String(40),nullable=False,server_default='road'), sa.Column('border_or_port',sa.String(160)),
        sa.Column('distance_km',sa.Float()), sa.Column('transit_days',sa.Float()), sa.Column('freight_total',sa.Float(),nullable=False,server_default='0'),
        sa.Column('currency',sa.String(10),nullable=False,server_default='USD'), sa.Column('insurance_percent',sa.Float(),nullable=False,server_default='0'), sa.Column('insurance_fixed',sa.Float(),nullable=False,server_default='0'),
        sa.Column('customs_total',sa.Float(),nullable=False,server_default='0'), sa.Column('destination_handling',sa.Float(),nullable=False,server_default='0'), sa.Column('other_cost',sa.Float(),nullable=False,server_default='0'),
        sa.Column('capacity_value',sa.Float()), sa.Column('capacity_unit',sa.String(30)), sa.Column('source_url',sa.Text()), sa.Column('source_title',sa.String(300)),
        sa.Column('verification_status',sa.String(30),nullable=False,server_default='Unverified'), sa.Column('assumptions',sa.JSON(),nullable=False,server_default='{}'), sa.Column('is_active',sa.Boolean(),nullable=False,server_default='1'),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for n,c in [('opportunity_id','opportunity_id'),('transport_mode','transport_mode'),('border_or_port','border_or_port'),('verification_status','verification_status'),('is_active','is_active')]: op.create_index('ix_logistics_scenarios_'+n,'logistics_scenarios',[c])
    for name,col,typ,default in [
        ('logistics_scenario_id','logistics_scenario_id',sa.Integer(),None),('incoterm','incoterm',sa.String(20),'CIF'),('cfr_total','cfr_total',sa.Float(),'0'),('cfr_unit_price','cfr_unit_price',sa.Float(),'0'),('landed_total','landed_total',sa.Float(),'0'),('landed_unit_price','landed_unit_price',sa.Float(),'0')]:
        op.add_column('commercial_offers',sa.Column(name,typ,nullable=True,server_default=default))
    with op.batch_alter_table('commercial_offers') as batch:
        batch.create_foreign_key('fk_commercial_offers_logistics_scenario','logistics_scenarios',['logistics_scenario_id'],['id'])
    op.create_index('ix_commercial_offers_logistics_scenario_id','commercial_offers',['logistics_scenario_id'])

def downgrade():
    op.drop_index('ix_commercial_offers_logistics_scenario_id',table_name='commercial_offers')
    with op.batch_alter_table('commercial_offers') as batch:
        batch.drop_constraint('fk_commercial_offers_logistics_scenario',type_='foreignkey')
    for c in ['landed_unit_price','landed_total','cfr_unit_price','cfr_total','incoterm','logistics_scenario_id']: op.drop_column('commercial_offers',c)
    for n in ['is_active','verification_status','border_or_port','transport_mode','opportunity_id']: op.drop_index('ix_logistics_scenarios_'+n,table_name='logistics_scenarios')
    op.drop_table('logistics_scenarios')
