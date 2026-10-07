"""freshness and expiration engine

Revision ID: 0030_freshness_engine
Revises: 0029_evidence_based_detection
"""
from alembic import op
import sqlalchemy as sa
revision="0030_freshness_engine"
down_revision="0029_evidence_based_detection"
branch_labels=None
depends_on=None

def upgrade():
    for table, cols in {
        "sources": [("freshness_status", sa.String(30)), ("freshness_score", sa.Float()), ("observed_at", sa.DateTime(timezone=True)), ("published_at", sa.DateTime(timezone=True)), ("updated_at_source", sa.DateTime(timezone=True)), ("expires_at", sa.DateTime(timezone=True)), ("last_verified_at", sa.DateTime(timezone=True))],
        "source_signals": [("freshness_status", sa.String(30)), ("freshness_score", sa.Float()), ("observed_at", sa.DateTime(timezone=True)), ("updated_at_source", sa.DateTime(timezone=True)), ("expires_at", sa.DateTime(timezone=True)), ("last_verified_at", sa.DateTime(timezone=True))],
        "demands": [("freshness_status", sa.String(30)), ("freshness_score", sa.Float()), ("observed_at", sa.DateTime(timezone=True)), ("updated_at_source", sa.DateTime(timezone=True)), ("expires_at", sa.DateTime(timezone=True)), ("last_verified_at", sa.DateTime(timezone=True))],
    }.items():
        for name, typ in cols:
            op.add_column(table, sa.Column(name, typ, nullable=True))


def downgrade():
    for table, names in [("demands", ["last_verified_at","expires_at","updated_at_source","observed_at","freshness_score","freshness_status"]),("source_signals", ["last_verified_at","expires_at","updated_at_source","observed_at","freshness_score","freshness_status"]),("sources", ["last_verified_at","expires_at","updated_at_source","published_at","observed_at","freshness_score","freshness_status"])]:
        for name in names: op.drop_column(table, name)
