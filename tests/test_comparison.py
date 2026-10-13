from types import SimpleNamespace
from app.services.comparison import compare_supplier_routes

def test_supplier_route_comparison_is_transparent_and_ranked():
    quotes=[SimpleNamespace(id=1,supplier_name='A',currency='USD',unit_price=10,quantity=1000,unit='kg',incoterm='EXW',freight_cost=0,other_cost=0,lead_time_days=5,status='Verified'),
            SimpleNamespace(id=2,supplier_name='B',currency='USD',unit_price=11,quantity=1000,unit='kg',incoterm='EXW',freight_cost=0,other_cost=0,lead_time_days=8,status='Unverified')]
    scenarios=[SimpleNamespace(id=1,name='Road',currency='USD',freight_total=500,insurance_percent=1,insurance_fixed=0,customs_total=0,destination_handling=0,other_cost=0,transit_days=3,verification_status='Verified',is_active=True),
               SimpleNamespace(id=2,name='Sea',currency='USD',freight_total=200,insurance_percent=1,insurance_fixed=0,customs_total=0,destination_handling=0,other_cost=0,transit_days=15,verification_status='Unverified',is_active=True)]
    rows=compare_supplier_routes(quotes,scenarios,base_currency='USD',fx_rates={'USD':1})
    ranked=[r for r in rows if r['comparable']]
    assert len(ranked)==4
    assert ranked[0]['rank']==1
    assert all('reasons' in r for r in ranked)

def test_missing_fx_does_not_guess():
    q=SimpleNamespace(id=1,supplier_name='A',currency='EUR',unit_price=10,quantity=100,unit='kg',incoterm='EXW',freight_cost=0,other_cost=0,lead_time_days=1,status='Verified')
    s=SimpleNamespace(id=1,name='Road',currency='USD',freight_total=10,insurance_percent=0,insurance_fixed=0,customs_total=0,destination_handling=0,other_cost=0,transit_days=1,verification_status='Verified',is_active=True)
    rows=compare_supplier_routes([q],[s],base_currency='USD',fx_rates={'USD':1})
    assert rows[0]['comparable'] is False
