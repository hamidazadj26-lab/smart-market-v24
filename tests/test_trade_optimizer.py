from app.services.trade_optimizer import optimize_trade_scenarios
from app.services.trade_route import calculate_trade_route

class Q:
    def __init__(self,id,name,currency='USD',unit_price=100,other_cost=10,status='Verified',lead_time_days=5,unit='kg',incoterm='EXW'):
        self.id=id; self.supplier_name=name; self.currency=currency; self.unit_price=unit_price; self.other_cost=other_cost; self.status=status; self.lead_time_days=lead_time_days; self.unit=unit; self.incoterm=incoterm
class R:
    def __init__(self,id,name,currency='USD',cost=50):
        self.id=id; self.name=name; self.currency=currency; self.verification_status='Verified'; self.calculation=calculate_trade_route([{'currency':currency,'freight_cost':cost,'border_cost':5,'transit_cost':5,'destination_handling':5,'other_cost':0,'distance_km':100,'transit_days':3}],10,currency,{})

def test_optimizer_builds_supplier_route_matrix():
    out=optimize_trade_scenarios(quotes=[Q(1,'A'),Q(2,'B',unit_price=120)],routes=[R(1,'R1'),R(2,'R2',cost=70)],quantity=10,target_currency='USD')
    assert out['scenario_count']==4
    assert out['scenarios'][0]['trade_unit_cost'] <= out['scenarios'][-1]['trade_unit_cost']

def test_optimizer_does_not_add_supplier_freight_again():
    q=Q(1,'A',unit_price=100,other_cost=0); q.freight_cost=999
    out=optimize_trade_scenarios(quotes=[q],routes=[R(1,'R1',cost=50)],quantity=10,target_currency='USD')
    assert out['scenarios'][0]['supplier_goods_total']==1000
    assert out['scenarios'][0]['route_cost']==65
    assert out['scenarios'][0]['total_trade_cost']==1065

def test_optimizer_requires_explicit_fx_for_cross_currency():
    try:
        optimize_trade_scenarios(quotes=[Q(1,'A',currency='EUR')],routes=[R(1,'R1')],quantity=10,target_currency='USD')
        assert False
    except ValueError as exc:
        assert 'Explicit FX rate' in str(exc)

def test_optimizer_uses_verified_import_component_when_explicit_customs_value():
    class Rule:
        id=7; currency='USD'; duty_percent=10; excise_percent=0; vat_percent=0; other_percent=0; fixed_fee=0
        vat_base='customs_plus_duty'; other_base='customs_value'
    out=optimize_trade_scenarios(quotes=[Q(1,'A',unit_price=100,other_cost=0)],routes=[R(1,'R1',cost=0)],quantity=10,target_currency='USD',import_rules={'1:1':Rule()},customs_values={'1:1':1000})
    assert out['scenarios'][0]['import_taxes_and_fees']==100
    assert out['scenarios'][0]['total_trade_cost']==1115
