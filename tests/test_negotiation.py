from app.services.negotiation import negotiation_engine

def test_negotiation_scenarios():
    x=negotiation_engine(landed_unit_cost=80, benchmark_unit_price=100, target_margin_percent=10, minimum_margin_percent=5, opening_buffer_percent=5, concession_steps=[0,5,10], quantity=100)
    assert x['minimum_acceptable_price']['unit_price'] > 80
    assert x['target_price']['unit_price'] > x['minimum_acceptable_price']['unit_price']
    assert len(x['concession_scenarios']) == 3

def test_invalid_margin():
    try: negotiation_engine(landed_unit_cost=80,target_margin_percent=10,minimum_margin_percent=20)
    except ValueError: return
    assert False
