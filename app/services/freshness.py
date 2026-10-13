from datetime import datetime, timezone
from dataclasses import dataclass

@dataclass(frozen=True)
class FreshnessResult:
    status: str
    score: float | None
    reference_at: datetime | None
    reason: str

POLICIES = {
    "purchase_demand": 14,
    "rfq": 30,
    "tender": 30,
    "listing": 45,
    "company_profile": 180,
    "news": 30,
    "default": 60,
}

def _days(now, dt):
    return max(0.0, (now-dt).total_seconds()/86400)

def evaluate_freshness(*, observed_at=None, published_at=None, updated_at=None, expires_at=None, now=None, policy="default") -> FreshnessResult:
    now = now or datetime.now(timezone.utc)
    reference = updated_at or published_at or observed_at
    if expires_at and expires_at <= now:
        return FreshnessResult("Expired", 0.0, expires_at, "explicit expiration reached")
    if reference is None:
        return FreshnessResult("Unknown", None, None, "no temporal evidence")
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    age = _days(now, reference)
    ttl = float(POLICIES.get(policy, POLICIES["default"]))
    if age <= ttl * .25: status = "Fresh"
    elif age <= ttl: status = "Recent"
    elif age <= ttl * 2: status = "Aging"
    else: status = "Stale"
    score = max(0.0, min(1.0, 1.0-age/(ttl*2)))
    return FreshnessResult(status, round(score,4), reference, f"age_days={round(age,2)}; ttl_days={int(ttl)}")

def apply_freshness(obj, **kwargs):
    r=evaluate_freshness(**kwargs)
    obj.freshness_status=r.status; obj.freshness_score=r.score
    return r
