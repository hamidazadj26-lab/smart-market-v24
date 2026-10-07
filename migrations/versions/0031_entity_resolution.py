"""entity resolution and identity graph
Revision ID: 0031_entity_resolution
Revises: 0030_freshness_engine
"""
from alembic import op
import sqlalchemy as sa
revision='0031_entity_resolution'; down_revision='0030_freshness_engine'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('entity_identities',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('entity_type',sa.String(30),nullable=False), sa.Column('entity_id',sa.Integer(),nullable=False), sa.Column('identity_type',sa.String(30),nullable=False), sa.Column('normalized_value',sa.String(500),nullable=False), sa.Column('source_id',sa.Integer(),nullable=True), sa.Column('evidence',sa.JSON(),nullable=True), sa.Column('confidence',sa.Float(),nullable=False,server_default='0'))
    op.create_index('ix_entity_identities_type','entity_identities',['entity_type']); op.create_index('ix_entity_identities_entity','entity_identities',['entity_id']); op.create_index('ix_entity_identities_value','entity_identities',['normalized_value'])
    op.create_table('entity_links',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('created_at',sa.DateTime(timezone=True),nullable=False), sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('left_type',sa.String(30),nullable=False), sa.Column('left_id',sa.Integer(),nullable=False), sa.Column('right_type',sa.String(30),nullable=False), sa.Column('right_id',sa.Integer(),nullable=False), sa.Column('relation',sa.String(30),nullable=False,server_default='possible_match'), sa.Column('score',sa.Float(),nullable=False,server_default='0'), sa.Column('reasons',sa.JSON(),nullable=True), sa.Column('evidence',sa.JSON(),nullable=True), sa.Column('reviewed',sa.Boolean(),nullable=False,server_default='0'))
    op.create_index('ix_entity_links_left','entity_links',['left_type','left_id']); op.create_index('ix_entity_links_right','entity_links',['right_type','right_id']); op.create_index('ix_entity_links_pair','entity_links',['left_type','left_id','right_type','right_id'],unique=True)

def downgrade():
    op.drop_index('ix_entity_links_pair',table_name='entity_links'); op.drop_index('ix_entity_links_right',table_name='entity_links'); op.drop_index('ix_entity_links_left',table_name='entity_links'); op.drop_table('entity_links')
    op.drop_index('ix_entity_identities_value',table_name='entity_identities'); op.drop_index('ix_entity_identities_entity',table_name='entity_identities'); op.drop_index('ix_entity_identities_type',table_name='entity_identities'); op.drop_table('entity_identities')
