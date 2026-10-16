"""Remove misleading zero defaults from derived commercial offer totals.

Revision ID: 0043_nullable_derived_offer_totals
Revises: 0042_entity_identity_integrity

Derived CFR and landed totals are unknown until calculated. Preserve existing
rows as-is; do not rewrite historical zeros because their meaning cannot be
inferred safely from the stored value alone.
"""
from alembic import op
import sqlalchemy as sa

revision = "0043_nullable_derived_offer_totals"
down_revision = "0042_entity_identity_integrity"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("commercial_offers") as batch:
        for column in (
            "cfr_total",
            "cfr_unit_price",
            "landed_total",
            "landed_unit_price",
        ):
            batch.alter_column(
                column,
                existing_type=sa.Float(),
                existing_nullable=True,
                existing_server_default=sa.text("0"),
                server_default=None,
            )


def downgrade():
    # Restoring the historical default is reversible at the schema level,
    # though new omitted values will again default to zero after downgrade.
    with op.batch_alter_table("commercial_offers") as batch:
        for column in (
            "cfr_total",
            "cfr_unit_price",
            "landed_total",
            "landed_unit_price",
        ):
            batch.alter_column(
                column,
                existing_type=sa.Float(),
                existing_nullable=True,
                server_default=sa.text("0"),
            )
