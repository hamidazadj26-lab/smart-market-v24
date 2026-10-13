"""Link opportunities to canonical supplier and buyer actors."""
from alembic import op
import sqlalchemy as sa

revision = "0039_opportunity_canonical_actors"
down_revision = "0038_intelligence_canonical_facts"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("opportunities") as batch:
        batch.add_column(sa.Column("supplier_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("buyer_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_opportunities_supplier_id", "suppliers", ["supplier_id"], ["id"])
        batch.create_foreign_key("fk_opportunities_buyer_id", "buyers", ["buyer_id"], ["id"])
    op.create_index("ix_opportunities_supplier_id", "opportunities", ["supplier_id"])
    op.create_index("ix_opportunities_buyer_id", "opportunities", ["buyer_id"])


def downgrade():
    op.drop_index("ix_opportunities_buyer_id", table_name="opportunities")
    op.drop_index("ix_opportunities_supplier_id", table_name="opportunities")
    with op.batch_alter_table("opportunities") as batch:
        batch.drop_constraint("fk_opportunities_buyer_id", type_="foreignkey")
        batch.drop_constraint("fk_opportunities_supplier_id", type_="foreignkey")
        batch.drop_column("buyer_id")
        batch.drop_column("supplier_id")
