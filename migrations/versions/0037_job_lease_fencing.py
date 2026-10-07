"""Fence stale discovery workers with a per-claim lease token."""
from alembic import op
import sqlalchemy as sa

revision = "0037_job_lease_fencing"
down_revision = "0036_job_heartbeat_recovery"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("discovery_jobs", sa.Column("lease_token", sa.String(length=64), nullable=True))
    op.create_index("ix_discovery_jobs_lease_token", "discovery_jobs", ["lease_token"])

def downgrade():
    op.drop_index("ix_discovery_jobs_lease_token", table_name="discovery_jobs")
    op.drop_column("discovery_jobs", "lease_token")
