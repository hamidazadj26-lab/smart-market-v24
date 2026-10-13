"""Evidence-aware trade opportunity radar.

This module ranks only records already stored in Smart Market. It does not
invent buyers, demand, prices, locations, FX rates, or proof of purchase.
"""
from __future__ import annotations
from datetime import datetime, timezone
from math import isfinite
from sqlalchemy.orm import Session

from ..models import (
    Opportunity, DiscoveryCandidate, Product, Customer, Manufacturer, Demand,
    SourceSignal, Market,
)
from .source_evidence import opportunity_source_intelligence


def _number(value, default=None):
    try:
        n = float(value)
        return n if isfinite(n) else default
    except (TypeError, ValueError):
        return default


def _unit(value):
    n = _number(value)
    if n is None:
        return None
    # Discovery confidence fields are stored as 0..1. Accept legacy 0..100
    # values explicitly, but never let out-of-range data distort a score.
    if n > 1 and n <= 100:
        n /= 100
    return max(0.0, min(1.0, n))


def _age_days(value, now):
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0.0, (now - value).total_seconds() / 86400)


def _freshness(value, now, half_life_days=30):
    age = _age_days(value, now)
    if age is None:
        return None
    return 0.5 ** (age / half_life_days)


def _score(parts):
    usable = [(weight, value) for weight, value in parts if value is not None]
    if not usable:
        return {"score": None, "coverage_pct": 0.0}
    denom = sum(weight for weight, _ in usable)
    if denom <= 0:
        return {"score": None, "coverage_pct": 0.0}
    return {
        "score": round(sum(weight * value for weight, value in usable) / denom * 100, 2),
        "coverage_pct": round(denom / sum(weight for weight, _ in parts) * 100, 2),
    }


def _next_action(*, verified, source_url, confidence, demand_likelihood, conflicts=0):
    if conflicts:
        return "Resolve conflicting evidence before outreach."
    if not source_url:
        return "Find and record a traceable public source before outreach."
    if not verified or (confidence or 0) < 0.65:
        return "Manually verify the company, buyer role, and current demand; seek an independent source."
    if (demand_likelihood or 0) >= 0.65:
        return "Confirm quantity, specification, delivery city, timing, and payment terms with the buyer."
    return "Qualify product fit and ask whether there is a current purchase requirement."


def build_trade_radar(db: Session, *, market: str | None = None, limit: int = 50) -> dict:
    """Return ranked opportunities and unlinked discovery candidates separately."""
    now = datetime.now(timezone.utc)
    limit = max(1, min(int(limit), 100))
    opp_q = db.query(Opportunity).filter(Opportunity.is_archived.is_(False))
    candidate_q = db.query(DiscoveryCandidate).filter(DiscoveryCandidate.is_archived.is_(False))
    market_label = market
    if market:
        exact = db.query(Market).filter(Market.name == market).first()
        if exact:
            opp_q = opp_q.filter(Opportunity.market_id == exact.id)
            candidate_q = candidate_q.filter(DiscoveryCandidate.country == exact.target_country)
        elif "→" in market:
            source, target = [x.strip() for x in market.split("→", 1)]
            manufacturers = db.query(Manufacturer.id).filter(Manufacturer.country == source).subquery()
            customers = db.query(Customer.id).filter(Customer.country == target).subquery()
            opp_q = opp_q.filter(Opportunity.manufacturer_id.in_(manufacturers), Opportunity.customer_id.in_(customers))
            candidate_q = candidate_q.filter(DiscoveryCandidate.country == target)
        else:
            candidate_q = candidate_q.filter(DiscoveryCandidate.country.ilike(market.strip()))
            opp_q = opp_q.filter(Opportunity.id == -1)  # ambiguous market labels never broaden results

    opportunities = []
    for op in opp_q.order_by(Opportunity.score.desc()).limit(limit).all():
        product = db.get(Product, op.product_id)
        customer = db.get(Customer, op.customer_id)
        manufacturer = db.get(Manufacturer, op.manufacturer_id)
        demand = db.get(Demand, op.demand_id) if op.demand_id else None
        intel = opportunity_source_intelligence(db, op)
        ev_score = _unit(intel.get("overall_score")) if int(intel.get("independent_sources", 0)) > 0 else None
        freshness_values = []
        for entity in (customer, manufacturer, demand):
            if entity:
                dt = getattr(entity, "retrieved_at", None) or getattr(entity, "published_at", None) or getattr(entity, "updated_at", None)
                val = _freshness(dt, now)
                if val is not None:
                    freshness_values.append(val)
        freshness = sum(freshness_values) / len(freshness_values) if freshness_values else None
        verification_values = []
        for entity in (customer, manufacturer, demand):
            status = getattr(entity, "verification_status", None) if entity else None
            if status:
                verification_values.append(1.0 if status.lower() == "verified" else (0.5 if "partial" in status.lower() else 0.0))
        verification = sum(verification_values) / len(verification_values) if verification_values else None
        base = _unit(op.score)
        if base is None and _number(op.score) is not None:
            base = _unit(op.score)
        ranked = _score([(0.40, base), (0.30, ev_score), (0.15, freshness), (0.15, verification)])
        source_urls = sorted({e.get("url") for group in intel.get("entities", {}).values() for e in group.get("chain", {}).get("evidence", []) if e.get("url")})
        demand_score = _unit(getattr(demand, "confidence", None)) if demand else None
        verified = bool(verification is not None and verification >= 0.99)
        action = _next_action(verified=verified, source_url=(source_urls[0] if source_urls else getattr(demand, "source_url", None) or getattr(customer, "source_url", None)), confidence=demand_score, demand_likelihood=_unit(getattr(demand, "confidence", None)) if demand else None, conflicts=int(intel.get("conflict_count", 0)))
        opportunities.append({
            "record_type": "opportunity", "id": op.id,
            "product": getattr(product, "name", None),
            "buyer": getattr(customer, "name", None), "buyer_country": getattr(customer, "country", None), "buyer_city": getattr(customer, "city", None),
            "manufacturer": getattr(manufacturer, "name", None), "market": market_label,
            "stage": op.opportunity_stage, "verification_status": op.verification_status,
            "score": ranked["score"], "score_coverage_pct": ranked["coverage_pct"],
            "source_score": round(ev_score * 100, 2) if ev_score is not None else None,
            "source_count": int(intel.get("independent_sources", 0)), "conflict_count": int(intel.get("conflict_count", 0)),
            "source_urls": source_urls[:10], "next_action": action,
            "score_method": "40% existing opportunity score, 30% source intelligence, 15% recency, 15% verification; renormalized over available dimensions.",
        })

    candidates = []
    for c in candidate_q.order_by(DiscoveryCandidate.updated_at.desc()).limit(limit * 3).all():
        if (c.status or "").lower() in {"rejected", "duplicate", "archived"}:
            continue
        signal = db.get(SourceSignal, c.source_signal_id) if c.source_signal_id else None
        conf = _unit(c.confidence)
        demand_likelihood = _unit(c.demand_likelihood)
        trust = _unit(c.trust_score)
        observed = (getattr(signal, "published_at", None) or getattr(signal, "observed_at", None) or getattr(signal, "retrieved_at", None)) if signal else c.updated_at
        fresh = _freshness(observed, now)
        # Evidence presence is a completeness indicator, not proof of truth.
        has_source = bool(c.source_url or getattr(signal, "source_url", None))
        evidence_completeness = 1.0 if has_source and c.evidence else (0.5 if has_source or c.evidence else None)
        ranked = _score([(0.35, demand_likelihood), (0.25, conf), (0.20, trust), (0.15, fresh), (0.05, evidence_completeness)])
        status = (c.status or "Review").lower()
        verified = status in {"verified", "qualified", "active"}
        url = c.source_url or (getattr(signal, "source_url", None) if signal else None)
        candidates.append({
            "record_type": "discovery_candidate", "id": c.id, "name": c.name,
            "product": c.product_name, "country": c.country, "city": c.city,
            "candidate_type": c.candidate_type, "status": c.status,
            "score": ranked["score"], "score_coverage_pct": ranked["coverage_pct"],
            "confidence": round(conf * 100, 2) if conf is not None else None,
            "demand_likelihood": round(demand_likelihood * 100, 2) if demand_likelihood is not None else None,
            "source_url": url, "source_title": c.source_title or (getattr(signal, "source_title", None) if signal else None),
            "observed_at": observed.isoformat() if observed else None,
            "next_action": _next_action(verified=verified, source_url=url, confidence=conf, demand_likelihood=demand_likelihood),
            "score_method": "35% demand likelihood, 25% extraction confidence, 20% source trust, 15% recency, 5% evidence completeness; renormalized over available dimensions.",
        })
    candidates.sort(key=lambda x: (x["score"] is not None, x["score"] or -1), reverse=True)
    opportunities.sort(key=lambda x: (x["score"] is not None, x["score"] or -1), reverse=True)
    return {
        "status": "ok", "market": market_label, "generated_at": now.isoformat(),
        "opportunity_count": len(opportunities), "candidate_count": len(candidates[:limit]),
        "opportunities": opportunities[:limit], "discovery_candidates": candidates[:limit],
        "guardrails": [
            "Discovery candidates are leads, not verified buyers or confirmed purchase orders.",
            "Scores rank available evidence; they are not calibrated probabilities of winning a sale.",
            "Missing dimensions reduce score coverage and are not imputed as positive evidence.",
            "No live external source is called and no record is modified by this read endpoint.",
        ],
    }
