"""Reconcile missing single-column ORM indexes without dropping legacy composites.

Revision ID: 0044_align_orm_single_column_indexes
Revises: 0043_nullable_derived_offer_totals
Create Date: 2026-10-16
"""
from alembic import op

revision = "0044_align_orm_single_column_indexes"
down_revision = "0043_nullable_derived_offer_totals"
branch_labels = None
depends_on = None


_INDEXES = (
    ("ix_ai_inferences_confidence", "ai_inferences", ("confidence",)),
    ("ix_ai_inferences_input_hash", "ai_inferences", ("input_hash",)),
    ("ix_buyers_city", "buyers", ("city",)),
    ("ix_buyers_is_archived", "buyers", ("is_archived",)),
    ("ix_buyers_verification_status", "buyers", ("verification_status",)),
    ("ix_commercial_facts_confidence", "commercial_facts", ("confidence",)),
    ("ix_commercial_facts_entity_id", "commercial_facts", ("entity_id",)),
    ("ix_commercial_facts_entity_type", "commercial_facts", ("entity_type",)),
    ("ix_commercial_facts_evidence_id", "commercial_facts", ("evidence_id",)),
    ("ix_commercial_facts_source_signal_id", "commercial_facts", ("source_signal_id",)),
    ("ix_commercial_facts_status", "commercial_facts", ("status",)),
    ("ix_commercial_facts_valid_until", "commercial_facts", ("valid_until",)),
    ("ix_country_profiles_verification_status", "country_profiles", ("verification_status",)),
    ("ix_discovery_jobs_created_by", "discovery_jobs", ("created_by",)),
    ("ix_discovery_usage_scope_key", "discovery_usage", ("scope_key",)),
    ("ix_discovery_usage_scope_type", "discovery_usage", ("scope_type",)),
    ("ix_discovery_usage_window_started_at", "discovery_usage", ("window_started_at",)),
    ("ix_entity_identities_identity_type", "entity_identities", ("identity_type",)),
    ("ix_entity_identities_source_id", "entity_identities", ("source_id",)),
    ("ix_entity_links_left_id", "entity_links", ("left_id",)),
    ("ix_entity_links_left_type", "entity_links", ("left_type",)),
    ("ix_entity_links_relation", "entity_links", ("relation",)),
    ("ix_entity_links_reviewed", "entity_links", ("reviewed",)),
    ("ix_entity_links_right_id", "entity_links", ("right_id",)),
    ("ix_entity_links_right_type", "entity_links", ("right_type",)),
    ("ix_fx_rates_base_currency", "fx_rates", ("base_currency",)),
    ("ix_fx_rates_confidence", "fx_rates", ("confidence",)),
    ("ix_fx_rates_expires_at", "fx_rates", ("expires_at",)),
    ("ix_fx_rates_quote_currency", "fx_rates", ("quote_currency",)),
    ("ix_fx_rates_source_id", "fx_rates", ("source_id",)),
    ("ix_fx_rates_status", "fx_rates", ("status",)),
    ("ix_landed_cost_calculations_status", "landed_cost_calculations", ("status",)),
    ("ix_opportunity_actions_action_type", "opportunity_actions", ("action_type",)),
    ("ix_suppliers_city", "suppliers", ("city",)),
    ("ix_suppliers_is_archived", "suppliers", ("is_archived",)),
    ("ix_suppliers_verification_status", "suppliers", ("verification_status",)),
    ("ix_trade_optimization_runs_created_by", "trade_optimization_runs", ("created_by",)),
    ("ix_trade_route_calculations_status", "trade_route_calculations", ("status",)),
    ("ix_trade_route_profiles_is_active", "trade_route_profiles", ("is_active",)),
    ("ix_trade_route_segments_segment_type", "trade_route_segments", ("segment_type",)),
)


def upgrade():
    # Deliberately add only indexes missing from the migrated schema.
    # Existing composite indexes are retained for queueing, entity lookup,
    # FX-pair lookup, opportunity recency, and market-price history.
    for name, table, columns in _INDEXES:
        op.create_index(name, table, list(columns), unique=False)


def downgrade():
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
