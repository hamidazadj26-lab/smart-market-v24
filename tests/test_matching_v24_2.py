from types import SimpleNamespace
from app.matching.scoring import calculate
from app.matching.engine import match
from app.opportunity.scoring import calculate as calculate_opportunity


def entities(**overrides):
    man = SimpleNamespace(product_id=1, capacity_value=100, confidence=0.8, latitude=35.7, longitude=51.4, is_archived=False)
    cus = SimpleNamespace(product_id=1, confidence=0.7, latitude=35.8, longitude=51.5, country='Afghanistan', is_archived=False)
    dem = SimpleNamespace(product_id=1, quantity=50, verification_status='Verified', confidence=0.9, country='Afghanistan', is_archived=False)
    for key, value in overrides.items():
        if key == 'man': man = SimpleNamespace(**{**man.__dict__, **value})
        elif key == 'cus': cus = SimpleNamespace(**{**cus.__dict__, **value})
        elif key == 'dem': dem = SimpleNamespace(**{**dem.__dict__, **value})
    return man, cus, dem


def test_unknown_dimensions_are_explicit_and_do_not_become_zero():
    man, cus, dem = entities(man={'capacity_value': None, 'confidence': 0}, cus={'latitude': None, 'longitude': None, 'confidence': 0})
    score = calculate(man, cus, dem)
    assert score.capacity is None
    assert score.trust is None
    assert score.location is None
    assert score.dimension_evidence['capacity']['status'] == 'Unknown'
    assert score.coverage < 100


def test_match_explanation_contains_dimension_evidence():
    man, cus, dem = entities()
    result = match(man, cus, dem)
    assert result['score'].total > 0
    assert 'dimension_evidence' in result['explanation']
    assert result['explanation']['coverage'] == result['score'].coverage


def test_opportunity_does_not_infer_actor_reliability_from_contact_fields():
    man, cus, dem = entities(man={'phone': 'x', 'website': 'x'}, cus={'phone': 'x', 'website': 'x'})
    m = calculate_opportunity(man, cus, dem, match=calculate(man, cus, dem))
    assert m.dimensions['buyer_reliability'] is None
    assert m.dimensions['supplier_reliability'] is None
