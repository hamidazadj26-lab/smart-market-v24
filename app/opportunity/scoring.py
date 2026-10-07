"""Evidence-aware opportunity scoring.

Only observed facts contribute numeric values. Unknown dimensions are omitted
from the weighted average and exposed explicitly in the explanation.
"""
from dataclasses import dataclass

DEFAULT_WEIGHTS = {
    'demand_strength': 25,
    'supply_fit': 20,
    'data_confidence': 15,
    'repeatability': 10,
    'logistics_fit': 10,
    'competition': 10,
    'buyer_reliability': 5,
    'supplier_reliability': 5,
}

@dataclass(frozen=True)
class OpportunityScore:
    total: float
    dimensions: dict
    confidence: float
    priority: str
    reasons: list[str]
    coverage: float


def _clamp(v):
    return max(0.0, min(100.0, float(v)))


def _status_score(status):
    return {'Verified': 100.0, 'Partially Verified': 60.0, 'Unverified': 25.0, 'Rejected': 0.0}.get(status)


def calculate(manufacturer, customer, demand, market=None, match=None, weights=None, actor_evidence=None):
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    actor_evidence = actor_evidence or {}

    demand_strength = _status_score(getattr(demand, 'verification_status', None))
    supply_fit = float(getattr(match, 'total', 0.0)) if match else None

    man_conf = getattr(manufacturer, 'confidence', None)
    cus_conf = getattr(customer, 'confidence', None)
    confidence_values = [float(x) for x in (man_conf, cus_conf) if x is not None and float(x) > 0]
    data_confidence = None
    if confidence_values:
        demand_conf = getattr(demand, 'confidence', None)
        all_conf = confidence_values + ([float(demand_conf)] if demand_conf is not None and float(demand_conf) > 0 else [])
        data_confidence = _clamp(sum(all_conf) / len(all_conf) * 100)

    repeatability = actor_evidence.get('repeatability')
    competition = actor_evidence.get('competition')
    buyer_reliability = actor_evidence.get('buyer_reliability')
    supplier_reliability = actor_evidence.get('supplier_reliability')
    logistics_fit = getattr(match, 'location', None) if match else None

    dims = {
        'demand_strength': demand_strength,
        'supply_fit': supply_fit,
        'data_confidence': data_confidence,
        'repeatability': repeatability,
        'logistics_fit': logistics_fit,
        'competition': competition,
        'buyer_reliability': buyer_reliability,
        'supplier_reliability': supplier_reliability,
    }
    dims = {k: (None if v is None else round(_clamp(v), 2)) for k, v in dims.items()}

    total_weight = sum(float(v) for v in w.values()) or 100.0
    used_weight = sum(float(w[k]) for k, v in dims.items() if v is not None)
    weighted = sum(dims[k] * float(w[k]) for k in dims if dims[k] is not None)
    total = round(weighted / used_weight, 2) if used_weight else 0.0
    coverage = round(used_weight / total_weight * 100, 2)

    confidence_components = [v for v in (data_confidence, demand_strength) if v is not None]
    confidence = round(sum(confidence_components) / len(confidence_components), 2) if confidence_components else 0.0
    if buyer_reliability is not None:
        confidence = round((confidence + buyer_reliability) / 2, 2)

    if total >= 80 and confidence >= 70 and coverage >= 70:
        priority = 'Hot'
    elif total >= 65 and coverage >= 55:
        priority = 'Warm'
    else:
        priority = 'Review'

    reasons = [
        f'{k}: {v:.0f}/100' if v is not None else f'{k}: نامشخص'
        for k, v in dims.items()
    ]
    reasons.append(f'پوشش شواهد: {coverage:.0f}٪')
    return OpportunityScore(total, dims, confidence, priority, reasons, coverage)
