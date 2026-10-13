from typing import Optional
from ..services.import_cost import calculate_import_cost


def _n(v):
    return float(v or 0)


def calculate_total_landed_cost(*, quantity: float, currency: str, supplier_cost: float,
                                packaging_cost: float = 0, inland_cost: float = 0,
                                export_cost: float = 0, freight_cost: float = 0,
                                insurance_cost: float = 0, customs_value: Optional[float] = None,
                                import_cost: Optional[dict] = None, destination_handling: float = 0,
                                other_cost: float = 0, fx_rate: Optional[float] = None,
                                expected_currency: Optional[str] = None):
    q=_n(quantity)
    if q <= 0: raise ValueError('quantity must be > 0')
    if _n(supplier_cost) < 0: raise ValueError('supplier_cost must be >= 0')
    if fx_rate is not None and _n(fx_rate) <= 0: raise ValueError('fx_rate must be > 0')
    if expected_currency and expected_currency != currency and fx_rate is None:
        raise ValueError('Explicit FX Rate is required when currencies differ')
    base_currency_total = _n(supplier_cost)+_n(packaging_cost)+_n(inland_cost)+_n(export_cost)
    customs = _n(customs_value) if customs_value is not None else 0.0
    if import_cost:
        customs = _n(import_cost.get('customs_value', customs))
        taxes = _n(import_cost.get('total_import_taxes_and_fees'))
        import_rule_id = import_cost.get('rule_id')
    else:
        taxes = 0.0; import_rule_id = None
    insurance = _n(insurance_cost)
    logistics_total = _n(freight_cost)+insurance+_n(destination_handling)+_n(other_cost)
    total = base_currency_total + _n(freight_cost) + insurance + taxes + _n(destination_handling) + _n(other_cost)
    return {
        'status':'Calculated', 'currency':currency, 'quantity':q,
        'supplier_cost':round(_n(supplier_cost),6), 'packaging_cost':round(_n(packaging_cost),6),
        'inland_cost':round(_n(inland_cost),6), 'export_cost':round(_n(export_cost),6),
        'freight_cost':round(_n(freight_cost),6), 'insurance_cost':round(insurance,6),
        'customs_value':round(customs,6), 'import_taxes_and_fees':round(taxes,6),
        'destination_handling':round(_n(destination_handling),6), 'other_cost':round(_n(other_cost),6),
        'total_landed_cost':round(total,6), 'landed_unit_cost':round(total/q,6),
        'fx_rate':fx_rate, 'import_cost_rule_id':import_rule_id,
        'assumptions':{
            'currency_conversion_explicit': fx_rate is not None,
            'customs_value_explicit': customs_value is not None or bool(import_cost),
            'freight_explicit': True, 'insurance_explicit': True,
            'destination_handling_explicit': True, 'other_cost_explicit': True,
        }
    }
