from app.services.landed_cost import calculate_total_landed_cost

def test_total_landed_cost_explicit_components():
    r=calculate_total_landed_cost(quantity=100,currency='USD',supplier_cost=5000,packaging_cost=100,inland_cost=200,export_cost=50,freight_cost=600,insurance_cost=50,customs_value=5000,import_cost={'customs_value':5000,'total_import_taxes_and_fees':550,'rule_id':7},destination_handling=100,other_cost=50)
    assert r['total_landed_cost']==6700
    assert r['landed_unit_cost']==67

def test_currency_difference_requires_fx():
    try: calculate_total_landed_cost(quantity=1,currency='OMR',supplier_cost=10,expected_currency='USD')
    except ValueError as e: assert 'FX Rate' in str(e)
    else: raise AssertionError('expected FX requirement')

def test_no_import_rule_does_not_invent_tax():
    r=calculate_total_landed_cost(quantity=10,currency='USD',supplier_cost=100,customs_value=None)
    assert r['import_taxes_and_fees']==0
    assert r['total_landed_cost']==100
