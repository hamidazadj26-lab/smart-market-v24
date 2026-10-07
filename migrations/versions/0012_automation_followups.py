"""V22.1 automation follow-up engine (no new tables)."""
from alembic import op

revision='0012_automation_followups'
down_revision='0011_opportunity_operating_system'
branch_labels=None
depends_on=None

def upgrade():
    # Automation is implemented as idempotent OpportunityAction records; no schema change required.
    pass

def downgrade():
    # No schema change to reverse.
    pass
