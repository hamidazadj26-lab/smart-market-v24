"""Add source metadata to discovery candidates."""
from alembic import op
import sqlalchemy as sa

revision = "0035_candidate_source_metadata"
down_revision = "0034_intelligent_discovery_controls"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("discovery_candidates", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("discovery_candidates", sa.Column("source_title", sa.String(length=300), nullable=True))


def downgrade():
    op.drop_column("discovery_candidates", "source_title")
    op.drop_column("discovery_candidates", "source_url")
