from typing import Optional
import math
from numbers import Real

from ..services.import_cost import calculate_import_cost


def _n(v, name: str = "value") -> float:
    """Convert a numeric input and reject booleans/non-finite values."""
    if v is None or v == "":
        return 0.0
    if isinstance(v, bool) or not isinstance(v, Real):
        raise TypeError(f"{name} must be a real number.")
    value = float(v)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    return value


def calculate_total_landed_cost(*, quantity: float, currency: str, supplier_cost: float,
                                packaging_cost: float = 0, inland_cost: float = 0,
                                export_cost: float = 0, freight_cost: float = 0,
                                insurance_cost: float = 0, customs_value: Optional[float] = None,
                                import_cost: Optional[dict] = None, destination_handling: float = 0,
                                other_cost: float = 0, fx_rate: Optional[float] = None,
                                expected_currency: Optional[str] = None):
    q = _n(quantity, "quantity")
    if q <= 0:
        raise ValueError("quantity must be > 0")

    costs = {
        "supplier_cost": _n(supplier_cost, "supplier_cost"),
        "packaging_cost": _n(packaging_cost, "packaging_cost"),
        "inland_cost": _n(inland_cost, "inland_cost"),
        "export_cost": _n(export_cost, "export_cost"),
        "freight_cost": _n(freight_cost, "freight_cost"),
        "insurance_cost": _n(insurance_cost, "insurance_cost"),
        "destination_handling": _n(destination_handling, "destination_handling"),
        "other_cost": _n(other_cost, "other_cost"),
    }
    for name, value in costs.items():
        if value < 0:
            raise ValueError(f"{name} must be >= 0")

    fx = None if fx_rate is None else _n(fx_rate, "fx_rate")
    if fx is not None and fx <= 0:
        raise ValueError("fx_rate must be > 0")
    if expected_currency and expected_currency != currency and fx is None:
        raise ValueError("Explicit FX Rate is required when currencies differ")

    customs = _n(customs_value, "customs_value") if customs_value is not None else 0.0
    taxes = 0.0
    import_rule_id = None
    if import_cost:
        if not isinstance(import_cost, dict):
            raise TypeError("import_cost must be a mapping.")
        customs = _n(import_cost.get("customs_value", customs), "import_cost.customs_value")
        taxes = _n(import_cost.get("total_import_taxes_and_fees"), "import_cost.total_import_taxes_and_fees")
        import_rule_id = import_cost.get("rule_id")
    if customs < 0:
        raise ValueError("customs_value must be >= 0")
    if taxes < 0:
        raise ValueError("total_import_taxes_and_fees must be >= 0")

    base_currency_total = costs["supplier_cost"] + costs["packaging_cost"] + costs["inland_cost"] + costs["export_cost"]
    insurance = costs["insurance_cost"]
    total = (base_currency_total + costs["freight_cost"] + insurance + taxes
             + costs["destination_handling"] + costs["other_cost"])
    if not math.isfinite(total):
        raise ValueError("total landed cost must be finite.")

    return {
        "status": "Calculated", "currency": currency, "quantity": q,
        "supplier_cost": round(costs["supplier_cost"], 6),
        "packaging_cost": round(costs["packaging_cost"], 6),
        "inland_cost": round(costs["inland_cost"], 6),
        "export_cost": round(costs["export_cost"], 6),
        "freight_cost": round(costs["freight_cost"], 6),
        "insurance_cost": round(insurance, 6),
        "customs_value": round(customs, 6),
        "import_taxes_and_fees": round(taxes, 6),
        "destination_handling": round(costs["destination_handling"], 6),
        "other_cost": round(costs["other_cost"], 6),
        "total_landed_cost": round(total, 6),
        "landed_unit_cost": round(total / q, 6),
        "fx_rate": fx, "import_cost_rule_id": import_rule_id,
        "assumptions": {
            "currency_conversion_explicit": fx is not None,
            "customs_value_explicit": customs_value is not None or bool(import_cost),
            "freight_explicit": True, "insurance_explicit": True,
            "destination_handling_explicit": True, "other_cost_explicit": True,
        }
    }
