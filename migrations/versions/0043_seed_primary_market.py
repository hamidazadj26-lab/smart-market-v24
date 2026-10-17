"""Seed the primary Iran-to-Afghanistan market when absent.

This migration is intentionally idempotent and never overwrites an existing
market profile or any commercial data.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0043_seed_primary_market"
down_revision = "0042_entity_identity_integrity"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    markets = sa.table(
        "markets",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String(200)),
        sa.column("source_country", sa.String(100)),
        sa.column("target_country", sa.String(100)),
        sa.column("active", sa.Boolean()),
        sa.column("default_currency", sa.String(10)),
        sa.column("languages", sa.JSON()),
        sa.column("incoterms", sa.JSON()),
        sa.column("transport_modes", sa.JSON()),
        sa.column("scoring_weights", sa.JSON()),
        sa.column("commercial_rules", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    name = "Iran → Afghanistan"
    exists = bind.execute(
        sa.select(markets.c.id).where(markets.c.name == name).limit(1)
    ).first()
    if exists:
        return

    now = datetime.now(timezone.utc)
    bind.execute(
        markets.insert().values(
            name=name,
            source_country="Iran",
            target_country="Afghanistan",
            active=True,
            default_currency="USD",
            languages=["fa", "ps", "en"],
            incoterms=["EXW", "FCA", "FOB", "CFR", "CIF", "DAP"],
            transport_modes=["road", "rail", "multimodal"],
            scoring_weights={
                "product_fit": 30,
                "capacity": 15,
                "demand": 25,
                "trust": 20,
                "location": 10,
            },
            commercial_rules={"customs_required": True},
            created_at=now,
            updated_at=now,
        )
    )


def downgrade():
    # Keep the seeded row: it may already be referenced by opportunities or
    # edited by the operator. Downgrade must not delete operational data.
    pass
