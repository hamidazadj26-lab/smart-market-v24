from types import SimpleNamespace
from app.services.market_intelligence import compare_supplier_quote_to_market


def test_supplier_quote_market_comparison():
    q=SimpleNamespace(id=7,supplier_name='Supplier A',unit_price=9.0,currency='USD',unit='kg',quantity=1000,freight_cost=500,other_cost=0)
    b=SimpleNamespace(weighted_median_price=10.0,median_price=10.0)
    r=compare_supplier_quote_to_market(q,b,target_currency='USD',target_unit='kg',fx_rates={'USD':1},unit_factors={})
    assert r['comparable'] is True
    assert r['normalized_landed_unit_cost']==9.5
    assert r['market_room_per_unit']==0.5


def test_missing_fx_does_not_guess():
    q=SimpleNamespace(id=8,supplier_name='Supplier B',unit_price=100.0,currency='EUR',unit='kg',quantity=100,freight_cost=0,other_cost=0)
    b=SimpleNamespace(weighted_median_price=110.0,median_price=110.0)
    r=compare_supplier_quote_to_market(q,b,target_currency='USD',target_unit='kg',fx_rates={'USD':1},unit_factors={})
    assert r['comparable'] is False
