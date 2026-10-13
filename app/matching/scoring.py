"""Evidence-aware, explainable opportunity matching.

The score consumes every decision dimension that is available. Unknown values are
never fabricated; they are omitted from the weighted average and exposed in the
breakdown. This keeps discovery conservative while allowing later commercial data
(price, logistics, corroborated evidence and reliability) to improve a match.
"""
from dataclasses import dataclass
import math

DEFAULT_WEIGHTS = {
    'product_fit': 20,
    'capacity': 10,
    'demand': 20,
    'trust': 15,
    'location': 5,
    'price': 10,
    'logistics': 10,
    'evidence': 5,
    'freshness': 3,
    'buyer_reliability': 2,
}

@dataclass(frozen=True)
class MatchScore:
    total: float
    product_fit: float
    capacity: float | None
    demand: float
    trust: float | None
    location: float | None
    distance_km: float | None
    priority: str
    reasons: list[str]
    dimension_evidence: dict
    coverage: float
    price: float | None = None
    logistics: float | None = None
    evidence: float | None = None
    freshness: float | None = None
    buyer_reliability: float | None = None
    supplier_reliability: float | None = None


def haversine(a, b, c, d):
    if None in (a, b, c, d): return None
    r = 6371.0088
    p1, p2 = math.radians(a), math.radians(c)
    dp = math.radians(c - a); dl = math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def _verification_score(status):
    return {'Verified': 100.0, 'Partially Verified': 60.0, 'Unverified': 25.0, 'Rejected': 0.0}.get(status)


def _clamp(value):
    return max(0.0, min(100.0, float(value)))


def _dimension(value, *, status, source, note):
    return {'value': None if value is None else round(_clamp(value), 2), 'status': status, 'source': source, 'note': note}


def calculate(man, cus, dem, weights=None, actor_evidence=None) -> MatchScore:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    actor_evidence = actor_evidence or {}

    if man.product_id == cus.product_id == dem.product_id:
        pf, pf_note = 100.0, 'هر سه رکورد به یک محصول متصل هستند.'
    elif man.product_id == dem.product_id or cus.product_id == dem.product_id:
        pf, pf_note = 80.0, 'دو مورد از سه رکورد به محصول تقاضا متصل هستند.'
    else:
        pf, pf_note = 0.0, 'اتصال محصول با تقاضا کامل نیست.'

    quantity = getattr(dem, 'quantity', None)
    capacity = getattr(man, 'capacity_value', None)
    if capacity is not None and quantity is not None:
        cap = 100.0 if float(capacity) >= float(quantity) else _clamp(float(capacity) / float(quantity) * 100)
        cap_status, cap_note = 'Known', 'ظرفیت تولیدکننده با مقدار تقاضا مقایسه شده است.'
    else:
        cap, cap_status, cap_note = None, 'Unknown', 'ظرفیت یا مقدار تقاضا ثبت نشده است.'

    demand_status = getattr(dem, 'verification_status', None) or 'Unverified'
    ds = _verification_score(demand_status)
    demand_note = f'وضعیت راستی‌آزمایی تقاضا: {demand_status}.'

    confs = [float(x) for x in (getattr(man, 'confidence', None), getattr(cus, 'confidence', None)) if x is not None]
    trust = _clamp(sum(confs) / len(confs) * 100) if any(x > 0 for x in confs) else None
    trust_status = 'Known' if trust is not None else 'Unknown'
    trust_note = 'اعتماد از confidence ثبت‌شده دو طرف محاسبه شده است.' if trust is not None else 'داده اعتماد کافی ثبت نشده است.'

    dist = haversine(getattr(man, 'latitude', None), getattr(man, 'longitude', None), getattr(cus, 'latitude', None), getattr(cus, 'longitude', None))
    if dist is not None:
        ls = 100.0 if dist < 500 else 80.0 if dist < 1000 else 60.0 if dist < 2000 else 35.0
        location_status, location_note = 'Known', 'امتیاز بر اساس فاصله جغرافیایی محاسبه شده است.'
    else:
        ls, location_status, location_note = None, 'Unknown', 'مختصات هر دو طرف کافی نیست.'

    # Optional commercial/operational facts are injected only when observed.
    price = actor_evidence.get('price')
    logistics = actor_evidence.get('logistics')
    evidence = actor_evidence.get('evidence')
    freshness = actor_evidence.get('freshness')
    buyer_rel = actor_evidence.get('buyer_reliability')
    supplier_rel = actor_evidence.get('supplier_reliability')

    dims = {
        'product_fit': _dimension(pf, status='Known', source='product_id', note=pf_note),
        'capacity': _dimension(cap, status='Known' if cap is not None else 'Unknown', source='capacity_value + demand.quantity', note=cap_note),
        'demand': _dimension(ds, status='Known', source='demand.verification_status', note=demand_note),
        'trust': _dimension(trust, status=trust_status, source='manufacturer/customer.confidence', note=trust_note),
        'location': _dimension(ls, status=location_status, source='latitude + longitude', note=location_note),
        'price': _dimension(price, status='Known' if price is not None else 'Unknown', source='commercial_price', note='قیمت فقط در صورت وجود داده تجاری معتبر وارد امتیاز می‌شود.'),
        'logistics': _dimension(logistics, status='Known' if logistics is not None else 'Unknown', source='logistics_scenario', note='تناسب لجستیکی فقط از سناریوی حمل محاسبه‌شده استفاده می‌کند.'),
        'evidence': _dimension(evidence, status='Known' if evidence is not None else 'Unknown', source='evidence_chain', note='امتیاز شواهد از منابع و شواهد ثبت‌شده می‌آید.'),
        'freshness': _dimension(freshness, status='Known' if freshness is not None else 'Unknown', source='observed_at/valid_until', note='تازگی بر اساس زمان مشاهده محاسبه می‌شود.'),
        'buyer_reliability': _dimension(buyer_rel, status='Known' if buyer_rel is not None else 'Unknown', source='buyer_outcomes', note='قابلیت اتکای خریدار فقط از سابقه مشاهده‌شده استفاده می‌کند.'),
    }

    weighted_sum = sum(dim['value'] * float(w.get(key, 0)) for key, dim in dims.items() if dim['value'] is not None)
    used_weight = sum(float(w.get(key, 0)) for key, dim in dims.items() if dim['value'] is not None)
    total_weight = sum(float(v) for v in w.values()) or 100.0
    total = round(weighted_sum / used_weight, 2) if used_weight else 0.0
    coverage = round(used_weight / total_weight * 100, 2)

    # Hot requires verified demand plus adequate evidence coverage; commercial
    # dimensions are allowed to remain unknown during early discovery.
    if demand_status == 'Verified' and total >= 80 and coverage >= 70:
        priority = 'Hot'
    elif total >= 65 and coverage >= 55:
        priority = 'Warm'
    else:
        priority = 'Review'

    reasons = [f'{k}: {v["value"]:.0f}/100' if v['value'] is not None else f'{k}: نامشخص' for k, v in dims.items()]
    reasons.append(f'پوشش ابعاد: {coverage:.0f}٪')
    return MatchScore(
        total, pf, cap, ds, trust, ls, dist, priority, reasons, dims, coverage,
        price, logistics, evidence, freshness, buyer_rel, supplier_rel,
    )
