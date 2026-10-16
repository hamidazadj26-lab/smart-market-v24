"""Regression tests for optional commercial-offer calculation fields.

The historical migration 0009 intentionally creates these columns nullable.
Draft offers may not yet have a confirmed Incoterm or calculated CFR/landed totals.
"""
from app.models.models import CommercialOffer


def test_commercial_offer_fields_match_nullable_migration_contract():
    expected_nullable = {
        "incoterm",
        "cfr_total",
        "cfr_unit_price",
        "landed_total",
        "landed_unit_price",
    }
    for name in expected_nullable:
        column = CommercialOffer.__table__.columns[name]
        assert column.nullable is True, f"{name} must remain nullable until known/calculated"


def test_derived_cost_fields_are_not_schema_required_for_draft_offer():
    # A database row must be able to represent an offer whose derived totals
    # have not yet been calculated, rather than forcing a fabricated zero.
    for name in ("cfr_total", "cfr_unit_price", "landed_total", "landed_unit_price"):
        assert CommercialOffer.__table__.columns[name].nullable is True
