"""Align transport-provider fields and freshness status nullability."""
from alembic import op
import sqlalchemy as sa

revision = "0041_align_transport_provider_and_freshness_schema"
down_revision = "0040_commercial_offer_fx_provenance"
branch_labels = None
depends_on = None


def upgrade():
    for name, typ, default in (
        ("default_currency", sa.String(10), "USD"),
        ("languages", sa.JSON(), sa.text("'[]'")),
        ("incoterms", sa.JSON(), sa.text("'[]'")),
        ("transport_modes", sa.JSON(), sa.text("'[]'")),
        ("scoring_weights", sa.JSON(), sa.text("'{}'")),
        ("commercial_rules", sa.JSON(), sa.text("'{}'")),
    ):
        op.add_column(
            "transport_providers",
            sa.Column(name, typ, nullable=False, server_default=default),
        )

    op.execute("UPDATE sources SET freshness_status = 'Unknown' WHERE freshness_status IS NULL")
    op.execute("UPDATE source_signals SET freshness_status = 'Unknown' WHERE freshness_status IS NULL")
    with op.batch_alter_table("sources") as batch:
        batch.alter_column("freshness_status", existing_type=sa.String(30), nullable=False, server_default="Unknown")
    with op.batch_alter_table("source_signals") as batch:
        batch.alter_column("freshness_status", existing_type=sa.String(30), nullable=False, server_default="Unknown")


def downgrade():
    with op.batch_alter_table("source_signals") as batch:
        batch.alter_column("freshness_status", existing_type=sa.String(30), nullable=True, server_default=None)
    with op.batch_alter_table("sources") as batch:
        batch.alter_column("freshness_status", existing_type=sa.String(30), nullable=True, server_default=None)
    for name in ("commercial_rules", "scoring_weights", "transport_modes", "incoterms", "languages", "default_currency"):
        op.drop_column("transport_providers", name)
