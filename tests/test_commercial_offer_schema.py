"""Regression tests for optional commercial-offer calculation fields.

Migration 0009 historically leaves these columns nullable. Derived CFR/landed
totals must remain unknown until calculated; missing values must not become
fabricated zeroes.
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


def test_derived_cost_fields_do_not_default_unknown_values_to_zero():
    for name in ("cfr_total", "cfr_unit_price", "landed_total", "landed_unit_price"):
        column = CommercialOffer.__table__.columns[name]
        assert column.default is None, f"{name} must not invent a zero before calculation"
