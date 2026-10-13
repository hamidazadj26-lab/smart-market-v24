from datetime import datetime, timezone
from types import SimpleNamespace
from app.services.import_cost import calculate_import_cost,is_current

def test_import_cost_math():
    r=SimpleNamespace(id=1,duty_percent=10,excise_percent=5,vat_percent=15,other_percent=2,fixed_fee=20,currency='USD',vat_base='customs_plus_duty',other_base='taxable_total',status='Verified',effective_from=None,effective_to=None)
    x=calculate_import_cost(r,1000,10)
    assert x['duty']==100
    assert x['excise']==55
    assert x['vat']==165.0
    assert x['other_tax_or_fee']==26.4
    assert x['total_import_taxes_and_fees']==366.4
    assert x['landed_before_other_logistics']==1366.4

def test_unverified_rule_not_current():
    r=SimpleNamespace(status='Unverified',effective_from=None,effective_to=None)
    assert is_current(r) is False
