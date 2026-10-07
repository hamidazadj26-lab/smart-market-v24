from types import SimpleNamespace
from app.matching.scoring import calculate


def entities(**overrides):
    man = SimpleNamespace(product_id=1, capacity_value=100, confidence=0.9, latitude=35.7, longitude=51.4)
    cus = SimpleNamespace(product_id=1, confidence=0.8, latitude=36.3, longitude=59.6)
    dem = SimpleNamespace(product_id=1, quantity=50, verification_status='Verified')
    for obj, vals in ((man, overrides.get('man', {})), (cus, overrides.get('cus', {})), (dem, overrides.get('dem', {}))):
        for k, v in vals.items(): setattr(obj, k, v)
    return man, cus, dem


def test_matching_consumes_optional_commercial_dimensions_when_observed():
    man, cus, dem = entities()
    score = calculate(man, cus, dem, actor_evidence={
        'price': 90, 'logistics': 80, 'evidence': 95, 'freshness': 90, 'buyer_reliability': 85,
    })
    assert score.price == 90
    assert score.logistics == 80
    assert score.evidence == 95
    assert score.freshness == 90
    assert score.buyer_reliability == 85
    assert score.coverage == 100
    assert score.total > 80


def test_matching_never_fabricates_unknown_commercial_dimensions():
    man, cus, dem = entities()
    score = calculate(man, cus, dem)
    assert score.price is None
    assert score.logistics is None
    assert score.evidence is None
    assert score.freshness is None
    assert score.buyer_reliability is None
