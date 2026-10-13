from types import SimpleNamespace

import pytest

from app.opportunity.scoring import DEFAULT_WEIGHTS, calculate


def entities():
    return (
        SimpleNamespace(confidence=0.8),
        SimpleNamespace(confidence=0.7),
        SimpleNamespace(verification_status="Verified", confidence=0.9),
    )


@pytest.mark.parametrize("weights", [
    {"demand_strength": -1},
    {"demand_strength": float("nan")},
    {"demand_strength": float("inf")},
    {"demand_strength": -float("inf")},
    {"demand_strength": "25"},
    {"demand_strength": True},
    {"made_up_dimension": 10},
])
def test_invalid_custom_weights_are_rejected(weights):
    with pytest.raises((TypeError, ValueError)):
        calculate(*entities(), weights=weights)


def test_weights_must_be_a_mapping():
    with pytest.raises(TypeError, match="mapping"):
        calculate(*entities(), weights=[25, 20])


def test_all_zero_weights_are_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        calculate(*entities(), weights={key: 0 for key in DEFAULT_WEIGHTS})


def test_partial_valid_overrides_keep_defaults_and_bounded_coverage():
    score = calculate(*entities(), weights={"demand_strength": 50})
    assert 0 < score.total <= 100
    assert 0 < score.coverage <= 100


def test_buyer_reliability_used_in_confidence_is_normalized():
    score = calculate(*entities(), actor_evidence={"buyer_reliability": 200})
    assert score.dimensions["buyer_reliability"] == 100
    assert 0 <= score.confidence <= 100


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_observed_dimension_is_rejected(bad_value):
    with pytest.raises(ValueError, match="finite"):
        calculate(*entities(), actor_evidence={"repeatability": bad_value})
