from alembic import op
import sqlalchemy as sa
revision='0019_import_cost_intelligence'; down_revision='0018_product_compliance'; branch_labels=None; depends_on=None
def upgrade():
    op.create_table('import_cost_rules',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('market_id',sa.Integer(),sa.ForeignKey('markets.id'),nullable=False),
        sa.Column('hs_code',sa.String(30),nullable=False),
        sa.Column('product_scope',sa.String(250)),
        sa.Column('duty_percent',sa.Float(),nullable=False,server_default='0'),
        sa.Column('excise_percent',sa.Float(),nullable=False,server_default='0'),
        sa.Column('vat_percent',sa.Float(),nullable=False,server_default='0'),
        sa.Column('other_percent',sa.Float(),nullable=False,server_default='0'),
        sa.Column('fixed_fee',sa.Float(),nullable=False,server_default='0'),
        sa.Column('currency',sa.String(10),nullable=False,server_default='USD'),
        sa.Column('vat_base',sa.String(40),nullable=False,server_default='customs_plus_duty'),
        sa.Column('other_base',sa.String(40),nullable=False,server_default='customs_value'),
        sa.Column('status',sa.String(30),nullable=False,server_default='Unverified'),
        sa.Column('authority',sa.String(250)), sa.Column('source_url',sa.Text()), sa.Column('source_title',sa.String(300)),
        sa.Column('published_at',sa.DateTime(timezone=True)), sa.Column('effective_from',sa.DateTime(timezone=True)), sa.Column('effective_to',sa.DateTime(timezone=True)),
        sa.Column('retrieved_at',sa.DateTime(timezone=True),nullable=False), sa.Column('notes',sa.Text()),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for n,c in [('ix_import_cost_rules_market_id',['market_id']),('ix_import_cost_rules_hs_code',['hs_code']),('ix_import_cost_rules_status',['status']),('ix_import_cost_rules_product_scope',['product_scope'])]: op.create_index(n,'import_cost_rules',c)
    op.create_index('ix_import_cost_rules_market_hs','import_cost_rules',['market_id','hs_code'])
def downgrade():
    op.drop_index('ix_import_cost_rules_market_hs',table_name='import_cost_rules')
    for n in ['ix_import_cost_rules_product_scope','ix_import_cost_rules_status','ix_import_cost_rules_hs_code','ix_import_cost_rules_market_id']: op.drop_index(n,table_name='import_cost_rules')
    op.drop_table('import_cost_rules')
