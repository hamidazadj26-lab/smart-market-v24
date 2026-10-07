"""Add canonical supplier/buyer, commercial facts, FX rates and AI provenance."""
from alembic import op
import sqlalchemy as sa

revision = "0038_intelligence_canonical_facts"
down_revision = "0037_job_lease_fencing"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_name", sa.String(250), nullable=False),
        sa.Column("country", sa.String(100), nullable=False, server_default="Iran"),
        sa.Column("city", sa.String(120)), sa.Column("address", sa.Text()),
        sa.Column("phone", sa.String(80)), sa.Column("website", sa.Text()),
        sa.Column("verification_status", sa.String(30), nullable=False, server_default="Unverified"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("canonical_key", sa.String(300), unique=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_suppliers_canonical_name", "suppliers", ["canonical_name"])
    op.create_index("ix_suppliers_country", "suppliers", ["country"])
    op.create_index("ix_suppliers_trust_score", "suppliers", ["trust_score"])
    op.create_index("ix_suppliers_canonical_key", "suppliers", ["canonical_key"])

    op.create_table(
        "buyers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_name", sa.String(250), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("city", sa.String(120)), sa.Column("address", sa.Text()),
        sa.Column("phone", sa.String(80)), sa.Column("website", sa.Text()),
        sa.Column("verification_status", sa.String(30), nullable=False, server_default="Potential"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("canonical_key", sa.String(300), unique=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_buyers_canonical_name", "buyers", ["canonical_name"])
    op.create_index("ix_buyers_country", "buyers", ["country"])
    op.create_index("ix_buyers_reliability_score", "buyers", ["reliability_score"])
    op.create_index("ix_buyers_canonical_key", "buyers", ["canonical_key"])

    op.create_table(
        "commercial_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("fact_type", sa.String(100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("source_signal_id", sa.Integer(), sa.ForeignKey("source_signals.id")),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("verification_evidence.id")),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="Unverified"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_commercial_facts_entity", "commercial_facts", ["entity_type", "entity_id"])
    op.create_index("ix_commercial_facts_fact_type", "commercial_facts", ["fact_type"])
    op.create_index("ix_commercial_facts_observed_at", "commercial_facts", ["observed_at"])

    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("base_currency", sa.String(10), nullable=False),
        sa.Column("quote_currency", sa.String(10), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id")),
        sa.Column("source_url", sa.Text()),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="Unverified"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fx_rates_pair", "fx_rates", ["base_currency", "quote_currency"])
    op.create_index("ix_fx_rates_observed_at", "fx_rates", ["observed_at"])

    op.create_table(
        "ai_inferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.String(80), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("model_version", sa.String(120), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64)),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_inferences_task_type", "ai_inferences", ["task_type"])
    op.create_index("ix_ai_inferences_generated_at", "ai_inferences", ["generated_at"])

    for name in [
        "price_score", "logistics_score", "evidence_score", "freshness_score",
        "buyer_reliability_score", "supplier_reliability_score",
    ]:
        op.add_column("opportunities", sa.Column(name, sa.Float(), nullable=True))
    op.add_column("opportunities", sa.Column("score_breakdown", sa.JSON(), nullable=False, server_default="{}"))
    with op.batch_alter_table("supplier_quotes") as batch:
        batch.add_column(sa.Column("supplier_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_supplier_quotes_supplier_id", "suppliers", ["supplier_id"], ["id"])
    op.create_index("ix_supplier_quotes_supplier_id", "supplier_quotes", ["supplier_id"])

def downgrade():
    op.drop_index("ix_supplier_quotes_supplier_id", table_name="supplier_quotes")
    with op.batch_alter_table("supplier_quotes") as batch:
        batch.drop_constraint("fk_supplier_quotes_supplier_id", type_="foreignkey")
        batch.drop_column("supplier_id")
    op.drop_column("opportunities", "score_breakdown")
    for name in ["supplier_reliability_score","buyer_reliability_score","freshness_score","evidence_score","logistics_score","price_score"]:
        op.drop_column("opportunities", name)
    op.drop_index("ix_ai_inferences_generated_at", table_name="ai_inferences")
    op.drop_index("ix_ai_inferences_task_type", table_name="ai_inferences")
    op.drop_table("ai_inferences")
    op.drop_index("ix_fx_rates_observed_at", table_name="fx_rates")
    op.drop_index("ix_fx_rates_pair", table_name="fx_rates")
    op.drop_table("fx_rates")
    op.drop_index("ix_commercial_facts_observed_at", table_name="commercial_facts")
    op.drop_index("ix_commercial_facts_fact_type", table_name="commercial_facts")
    op.drop_index("ix_commercial_facts_entity", table_name="commercial_facts")
    op.drop_table("commercial_facts")
    op.drop_index("ix_buyers_canonical_key", table_name="buyers")
    op.drop_index("ix_buyers_reliability_score", table_name="buyers")
    op.drop_index("ix_buyers_country", table_name="buyers")
    op.drop_index("ix_buyers_canonical_name", table_name="buyers")
    op.drop_table("buyers")
    op.drop_index("ix_suppliers_canonical_key", table_name="suppliers")
    op.drop_index("ix_suppliers_trust_score", table_name="suppliers")
    op.drop_index("ix_suppliers_country", table_name="suppliers")
    op.drop_index("ix_suppliers_canonical_name", table_name="suppliers")
    op.drop_table("suppliers")
