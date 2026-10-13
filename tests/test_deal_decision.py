from app.services.commercial import deal_decision_engine

def test_deal_decision_engine_basic():
    x=deal_decision_engine(landed_unit_cost=80, benchmark_unit_price=100, target_margin_percent=20, minimum_margin_percent=10, quantity=100)
    assert round(x['target_price']['sell_unit_price'],6)==100
    assert round(x['market_room_per_unit'],6)==20
    assert x['target_margin_supported_at_benchmark_exact'] is True

def test_deal_decision_engine_commission():
    x=deal_decision_engine(landed_unit_cost=80, benchmark_unit_price=100, target_margin_percent=10, selling_commission_percent=5)
    assert x['target_price']['sell_unit_price'] > 80
    assert x['target_price']['margin_percent'] >= 10
