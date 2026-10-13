import pytest
from app.services.trade_route import calculate_trade_route

def test_route_aggregates_costs_and_distance():
    r=calculate_trade_route([
      {'from_location':'A','to_location':'Border','freight_cost':100,'border_cost':20,'transit_cost':5,'distance_km':100,'transit_days':1,'currency':'USD'},
      {'from_location':'Border','to_location':'B','freight_cost':80,'border_cost':10,'transit_cost':15,'destination_handling':25,'distance_km':200,'transit_days':2,'currency':'USD'}
    ],10)
    assert r['total_route_cost']==255
    assert r['route_unit_cost']==25.5
    assert r['distance_km']==300
    assert r['transit_days']==3

def test_route_requires_fx_for_currency_change():
    with pytest.raises(ValueError):
        calculate_trade_route([{'from_location':'A','to_location':'B','freight_cost':100,'currency':'EUR'}],10,'USD')
    r=calculate_trade_route([{'from_location':'A','to_location':'B','freight_cost':100,'currency':'EUR'}],10,'USD',{'EUR':1.1,'USD':1})
    assert r['freight_total']==110
