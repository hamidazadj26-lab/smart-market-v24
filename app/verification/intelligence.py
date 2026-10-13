from __future__ import annotations
from datetime import datetime, timezone
from difflib import SequenceMatcher
import re
from sqlalchemy.orm import Session
from ..models import Source, SourceTrust, SourceSignal, VerificationEvidence, Customer, DiscoveryCandidate

SOURCE_BASE = {
    'official website': 0.90,
    'official_company_website': 0.90,
    'rfq': 0.88,
    'tender': 0.86,
    'google places': 0.65,
    'google_places': 0.65,
    'public directory': 0.55,
    'directory': 0.55,
    'manual': 0.50,
    'firecrawl web': 0.50,
    'telegram': 0.45,
    'whatsapp business': 0.55,
}

def norm(v: str | None) -> str:
    if not v: return ''
    x = v.lower().strip()
    x = re.sub(r'[\u200c\u200f\u202a-\u202e]', '', x)
    x = re.sub(r'[^\w\u0600-\u06ff]+', ' ', x, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', x).strip()

def canonical_key(name: str | None, country: str | None, city: str | None = None) -> str:
    return '|'.join([norm(name), norm(country), norm(city)])

def similarity(a: str | None, b: str | None) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio() if a and b else 0.0

def source_trust(db: Session, source: Source | None, channel: str | None = None) -> float:
    if not source:
        return SOURCE_BASE.get(norm(channel), 0.40)
    row = db.query(SourceTrust).filter(SourceTrust.source_id == source.id).first()
    if row:
        return max(0.0, min(1.0, row.overall_score))
    key = norm(channel or source.source_type or source.name)
    base = SOURCE_BASE.get(key, SOURCE_BASE.get(norm(source.source_type), 0.50))
    row = SourceTrust(source_id=source.id, base_score=base, reliability_score=base,
                      freshness_score=0.70, identity_score=0.60, overall_score=base,
                      rationale={'initialized_from': key})
    db.add(row)
    db.flush()
    return base

def evidence_score(db: Session, entity_type: str, entity_id: int) -> dict:
    evs = db.query(VerificationEvidence).filter(
        VerificationEvidence.entity_type == entity_type,
        VerificationEvidence.entity_id == entity_id,
    ).all()
    if not evs:
        return {'score': 0.0, 'count': 0, 'independent_sources': 0, 'evidence': []}
    vals=[]; source_ids=set(); evidence=[]
    for ev in evs:
        signal = db.get(SourceSignal, ev.source_signal_id) if ev.source_signal_id else None
        source = db.get(Source, signal.source_id) if signal and signal.source_id else None
        trust = source_trust(db, source, ev.details.get('channel') if ev.details else None)
        val = max(0.0, min(1.0, ev.weight * trust))
        vals.append(val)
        if source and source.id: source_ids.add(source.id)
        evidence.append({'id': ev.id, 'type': ev.evidence_type, 'weight': ev.weight, 'source_trust': trust, 'url': ev.source_url})
    corroboration = min(0.20, max(0, len(source_ids)-1) * 0.05)
    score = min(1.0, (sum(vals) / len(vals)) + corroboration)
    return {'score': round(score, 4), 'count': len(evs), 'independent_sources': len(source_ids), 'evidence': evidence}

def update_candidate_trust(db: Session, candidate: DiscoveryCandidate) -> dict:
    ev = evidence_score(db, 'discovery_candidate', candidate.id)
    candidate.trust_score = max(candidate.confidence or 0, ev['score'])
    return ev

def find_candidate_duplicates(db: Session, candidate: DiscoveryCandidate) -> list[DiscoveryCandidate]:
    if not candidate.name: return []
    qs = db.query(DiscoveryCandidate).filter(
        DiscoveryCandidate.id != candidate.id,
        DiscoveryCandidate.is_archived == False,
    )
    out=[]
    for other in qs.all():
        if candidate.country and other.country and norm(candidate.country) != norm(other.country): continue
        name_score=similarity(candidate.name, other.name)
        city_score=1.0 if not candidate.city or not other.city else similarity(candidate.city, other.city)
        product_score=1.0 if not candidate.product_name or not other.product_name else similarity(candidate.product_name, other.product_name)
        total=0.60*name_score+0.20*city_score+0.20*product_score
        if total >= 0.86: out.append(other)
    return sorted(out, key=lambda x: (x.trust_score or 0, x.confidence or 0), reverse=True)

def merge_candidate(db: Session, winner: DiscoveryCandidate, duplicate: DiscoveryCandidate) -> DiscoveryCandidate:
    winner.confidence=max(winner.confidence or 0, duplicate.confidence or 0)
    winner.demand_likelihood=max(winner.demand_likelihood or 0, duplicate.demand_likelihood or 0)
    winner.trust_score=max(winner.trust_score or 0, duplicate.trust_score or 0)
    if not winner.source_url: winner.source_url=duplicate.source_url
    if not winner.source_title: winner.source_title=duplicate.source_title
    if not winner.activity_type: winner.activity_type=duplicate.activity_type
    if not winner.product_name: winner.product_name=duplicate.product_name
    winner.evidence={**(duplicate.evidence or {}), **(winner.evidence or {})}
    duplicate.duplicate_of_id=winner.id
    duplicate.is_archived=True
    return winner
