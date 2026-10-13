"""add rfq and communication center
Revision ID: 0007_rfq_communications
Revises: 0006_opportunity_actions
"""
from alembic import op
import sqlalchemy as sa
revision='0007_rfq_communications'
down_revision='0006_opportunity_actions'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('rfq_documents',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('channel',sa.String(30),nullable=False,server_default='whatsapp'),
        sa.Column('language',sa.String(10),nullable=False,server_default='en'),
        sa.Column('title',sa.String(250),nullable=False),
        sa.Column('body',sa.Text(),nullable=False),
        sa.Column('status',sa.String(30),nullable=False,server_default='Draft'),
        sa.Column('sent_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('response_due_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('metadata',sa.JSON(),nullable=False,server_default='{}'),
        sa.Column('created_by',sa.Integer(),sa.ForeignKey('admins.id'),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_rfq_documents_opportunity_id','rfq_documents',['opportunity_id'])
    op.create_index('ix_rfq_documents_channel','rfq_documents',['channel'])
    op.create_index('ix_rfq_documents_status','rfq_documents',['status'])
    op.create_index('ix_rfq_documents_created_by','rfq_documents',['created_by'])
    op.create_table('communication_logs',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('opportunity_id',sa.Integer(),sa.ForeignKey('opportunities.id'),nullable=False),
        sa.Column('rfq_id',sa.Integer(),sa.ForeignKey('rfq_documents.id'),nullable=True),
        sa.Column('channel',sa.String(30),nullable=False),
        sa.Column('direction',sa.String(20),nullable=False,server_default='outbound'),
        sa.Column('status',sa.String(30),nullable=False,server_default='Draft'),
        sa.Column('recipient',sa.String(250),nullable=True),
        sa.Column('subject',sa.String(250),nullable=True),
        sa.Column('message',sa.Text(),nullable=False),
        sa.Column('sent_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('response_summary',sa.Text(),nullable=True),
        sa.Column('created_by',sa.Integer(),sa.ForeignKey('admins.id'),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for n,c in [('opportunity_id','opportunity_id'),('rfq_id','rfq_id'),('channel','channel'),('status','status'),('created_by','created_by')]:
        op.create_index('ix_communication_logs_'+n,'communication_logs',[c])

def downgrade():
    for n in ['created_by','status','channel','rfq_id','opportunity_id']:
        op.drop_index('ix_communication_logs_'+n,table_name='communication_logs')
    op.drop_table('communication_logs')
    for n in ['created_by','status','channel','opportunity_id']:
        op.drop_index('ix_rfq_documents_'+n,table_name='rfq_documents')
    op.drop_table('rfq_documents')
