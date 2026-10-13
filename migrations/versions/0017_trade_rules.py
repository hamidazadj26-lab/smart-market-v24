from alembic import op
import sqlalchemy as sa
revision='0017_trade_rules'; down_revision='0016_multi_market'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('country_profiles',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('country_code',sa.String(10),nullable=False),
        sa.Column('country_name',sa.String(120),nullable=False),
        sa.Column('currencies',sa.JSON(),nullable=False,server_default='[]'),
        sa.Column('languages',sa.JSON(),nullable=False,server_default='[]'),
        sa.Column('payment_methods',sa.JSON(),nullable=False,server_default='[]'),
        sa.Column('customs_notes',sa.JSON(),nullable=False,server_default='{}'),
        sa.Column('logistics_nodes',sa.JSON(),nullable=False,server_default='[]'),
        sa.Column('source_url',sa.Text(),nullable=True),
        sa.Column('source_title',sa.String(300),nullable=True),
        sa.Column('retrieved_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('verification_status',sa.String(30),nullable=False,server_default='Unverified'),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('country_code'))
    op.create_index('ix_country_profiles_country_code','country_profiles',['country_code'])
    op.create_index('ix_country_profiles_country_name','country_profiles',['country_name'])
    op.create_table('trade_rules',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('market_id',sa.Integer(),sa.ForeignKey('markets.id'),nullable=False),
        sa.Column('country_profile_id',sa.Integer(),sa.ForeignKey('country_profiles.id'),nullable=True),
        sa.Column('rule_type',sa.String(50),nullable=False),
        sa.Column('title',sa.String(300),nullable=False),
        sa.Column('hs_code',sa.String(30),nullable=True),
        sa.Column('product_scope',sa.String(250),nullable=True),
        sa.Column('mandatory',sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column('status',sa.String(30),nullable=False,server_default='Unverified'),
        sa.Column('requirement',sa.Text(),nullable=False),
        sa.Column('documents',sa.JSON(),nullable=False,server_default='[]'),
        sa.Column('authority',sa.String(250),nullable=True),
        sa.Column('source_url',sa.Text(),nullable=True),
        sa.Column('source_title',sa.String(300),nullable=True),
        sa.Column('published_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('effective_from',sa.DateTime(timezone=True),nullable=True),
        sa.Column('effective_to',sa.DateTime(timezone=True),nullable=True),
        sa.Column('retrieved_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('notes',sa.Text(),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for name,cols in [('ix_trade_rules_market_id',['market_id']),('ix_trade_rules_country_profile_id',['country_profile_id']),('ix_trade_rules_rule_type',['rule_type']),('ix_trade_rules_hs_code',['hs_code']),('ix_trade_rules_product_scope',['product_scope']),('ix_trade_rules_mandatory',['mandatory']),('ix_trade_rules_status',['status'])]: op.create_index(name,'trade_rules',cols)
    op.create_index('ix_trade_rules_market_scope','trade_rules',['market_id','product_scope'])

def downgrade():
    op.drop_index('ix_trade_rules_market_scope',table_name='trade_rules')
    for n in ['ix_trade_rules_status','ix_trade_rules_mandatory','ix_trade_rules_product_scope','ix_trade_rules_hs_code','ix_trade_rules_rule_type','ix_trade_rules_country_profile_id','ix_trade_rules_market_id']: op.drop_index(n,table_name='trade_rules')
    op.drop_table('trade_rules')
    op.drop_index('ix_country_profiles_country_name',table_name='country_profiles'); op.drop_index('ix_country_profiles_country_code',table_name='country_profiles'); op.drop_table('country_profiles')
