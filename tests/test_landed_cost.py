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


import pytest


@pytest.mark.parametrize("field", [
    "supplier_cost", "packaging_cost", "inland_cost", "export_cost",
    "freight_cost", "insurance_cost", "destination_handling", "other_cost",
])
@pytest.mark.parametrize("bad_value", [-1, float("nan"), float("inf"), -float("inf")])
def test_invalid_cost_components_are_rejected(field, bad_value):
    kwargs = {"quantity": 1, "currency": "USD", "supplier_cost": 1, field: bad_value}
    with pytest.raises((TypeError, ValueError)):
        calculate_total_landed_cost(**kwargs)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf"), 0, -1])
def test_invalid_fx_rates_are_rejected(bad_value):
    with pytest.raises(ValueError):
        calculate_total_landed_cost(
            quantity=1, currency="USD", supplier_cost=10,
            fx_rate=bad_value, expected_currency="EUR",
        )


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf"), -1])
def test_invalid_import_taxes_are_rejected(bad_value):
    with pytest.raises((TypeError, ValueError)):
        calculate_total_landed_cost(
            quantity=1, currency="USD", supplier_cost=10,
            import_cost={"total_import_taxes_and_fees": bad_value},
        )


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf"), -1])
def test_invalid_customs_values_are_rejected(bad_value):
    with pytest.raises((TypeError, ValueError)):
        calculate_total_landed_cost(
            quantity=1, currency="USD", supplier_cost=10, customs_value=bad_value,
        )


def test_boolean_cost_is_rejected_as_invalid_numeric_input():
    with pytest.raises(TypeError):
        calculate_total_landed_cost(
            quantity=1, currency="USD", supplier_cost=True,
        )
