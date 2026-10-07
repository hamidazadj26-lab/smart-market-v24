"""verification intelligence
Revision ID: 0004_verification_intelligence
Revises: 0003_signal_provenance
"""
from alembic import op
import sqlalchemy as sa
revision='0004_verification_intelligence'
down_revision='0003_signal_provenance'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('source_trust',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('base_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('reliability_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('freshness_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('identity_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('overall_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('rationale', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_source_trust_source_id','source_trust',['source_id'],unique=True)
    op.create_index('ix_source_trust_overall_score','source_trust',['overall_score'])
    op.create_table('verification_evidence',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('entity_type',sa.String(60),nullable=False),
        sa.Column('entity_id',sa.Integer(),nullable=False),
        sa.Column('source_signal_id',sa.Integer(),sa.ForeignKey('source_signals.id')),
        sa.Column('evidence_type',sa.String(80),nullable=False),
        sa.Column('weight',sa.Float(),nullable=False,server_default='0.5'),
        sa.Column('excerpt',sa.Text()),
        sa.Column('source_url',sa.Text()),
        sa.Column('details',sa.JSON(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
    )
    for name,col in [('entity_type','entity_type'),('entity_id','entity_id'),('source_signal_id','source_signal_id'),('evidence_type','evidence_type')]:
        op.create_index('ix_verification_evidence_'+name,'verification_evidence',[col])
    op.add_column('discovery_candidates',sa.Column('canonical_key',sa.String(300),nullable=True))
    op.add_column('discovery_candidates',sa.Column('duplicate_of_id',sa.Integer(),nullable=True))
    op.add_column('discovery_candidates',sa.Column('trust_score',sa.Float(),nullable=False,server_default='0'))
    op.create_index('ix_discovery_candidates_canonical_key','discovery_candidates',['canonical_key'])
    op.create_index('ix_discovery_candidates_duplicate_of_id','discovery_candidates',['duplicate_of_id'])
    op.create_index('ix_discovery_candidates_trust_score','discovery_candidates',['trust_score'])

def downgrade():
    for name in ('trust_score','duplicate_of_id','canonical_key'):
        op.drop_index('ix_discovery_candidates_'+name, table_name='discovery_candidates')
    op.drop_column('discovery_candidates','trust_score')
    op.drop_column('discovery_candidates','duplicate_of_id')
    op.drop_column('discovery_candidates','canonical_key')
    for name in ('evidence_type','source_signal_id','entity_id','entity_type'):
        op.drop_index('ix_verification_evidence_'+name, table_name='verification_evidence')
    op.drop_table('verification_evidence')
    op.drop_index('ix_source_trust_overall_score',table_name='source_trust')
    op.drop_index('ix_source_trust_source_id',table_name='source_trust')
    op.drop_table('source_trust')
