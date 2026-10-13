"""Attach commercial offers to source-backed FX provenance."""
from alembic import op
import sqlalchemy as sa

revision = "0040_commercial_offer_fx_provenance"
down_revision = "0039_opportunity_canonical_actors"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("commercial_offers") as batch:
        batch.add_column(sa.Column("fx_rate_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_commercial_offers_fx_rate_id", "fx_rates", ["fx_rate_id"], ["id"])
    op.create_index("ix_commercial_offers_fx_rate_id", "commercial_offers", ["fx_rate_id"])


def downgrade():
    op.drop_index("ix_commercial_offers_fx_rate_id", table_name="commercial_offers")
    with op.batch_alter_table("commercial_offers") as batch:
        batch.drop_constraint("fk_commercial_offers_fx_rate_id", type_="foreignkey")
        batch.drop_column("fx_rate_id")
