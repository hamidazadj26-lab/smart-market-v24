"""Add discovery job heartbeat for stale worker recovery."""
from alembic import op
import sqlalchemy as sa

revision = "0036_job_heartbeat_recovery"
down_revision = "0035_candidate_source_metadata"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("discovery_jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_discovery_jobs_status_heartbeat", "discovery_jobs", ["status", "heartbeat_at"] )

def downgrade():
    op.drop_index("ix_discovery_jobs_status_heartbeat", table_name="discovery_jobs")
    op.drop_column("discovery_jobs", "heartbeat_at")
