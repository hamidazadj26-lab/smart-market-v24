from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlparse
import re
from sqlalchemy.orm import Session

from ..models import Source, SourceTrust, SourceSignal, VerificationEvidence, Verification
from ..verification.intelligence import source_trust, norm


def _dt(v):
    if not v:
        return None
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


def freshness_score(observed_at, half_life_days: int = 30) -> float:
    if not observed_at:
        return 0.25
    age = max(0.0, (datetime.now(timezone.utc) - _dt(observed_at)).total_seconds() / 86400)
    return round(0.5 ** (age / max(1, half_life_days)), 4)


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower().split(':')[0]
        return host[4:] if host.startswith('www.') else host
    except Exception:
        return None


def _claim(ev: VerificationEvidence) -> tuple[str, str] | None:
    details = ev.details or {}
    key = details.get('claim_key') or details.get('field') or ev.evidence_type
    value = details.get('claim_value')
    if value is None:
        value = details.get('value')
    if value is None and ev.excerpt:
        value = re.sub(r'\s+', ' ', ev.excerpt).strip()
    if value is None:
        return None
    return norm(str(key)), norm(str(value))


def evidence_chain(db: Session, entity_type: str, entity_id: int) -> dict:
    evs = db.query(VerificationEvidence).filter(
        VerificationEvidence.entity_type == entity_type,
        VerificationEvidence.entity_id == entity_id,
    ).order_by(VerificationEvidence.created_at.desc()).all()
    rows = []
    source_ids = set()
    domains = set()
    claim_groups: dict[str, list[dict]] = {}
    for ev in evs:
        signal = db.get(SourceSignal, ev.source_signal_id) if ev.source_signal_id else None
        source = db.get(Source, signal.source_id) if signal and signal.source_id else None
        observed = getattr(signal, 'published_at', None) or getattr(signal, 'retrieved_at', None) or ev.created_at
        trust = source_trust(db, source, (ev.details or {}).get('channel'))
        domain = _domain(ev.source_url or getattr(signal, 'source_url', None) or getattr(source, 'base_url', None))
        if source:
            source_ids.add(source.id)
        if domain:
            domains.add(domain)
        claim = _claim(ev)
        item = {
            'evidence_id': ev.id,
            'evidence_type': ev.evidence_type,
            'source_id': source.id if source else None,
            'source_name': source.name if source else None,
            'source_type': source.source_type if source else None,
            'source_trust': round(trust, 4),
            'domain': domain,
            'observed_at': observed.isoformat() if observed else None,
            'freshness': freshness_score(observed),
            'weight': ev.weight,
            'url': ev.source_url or getattr(signal, 'source_url', None),
            'excerpt': ev.excerpt,
            'claim_key': claim[0] if claim else None,
            'claim_value': claim[1] if claim else None,
        }
        rows.append(item)
        if claim:
            claim_groups.setdefault(claim[0], []).append(item)

    conflicts = []
    for key, claims in claim_groups.items():
        values = {}
        for item in claims:
            if item['claim_value']:
                values.setdefault(item['claim_value'], []).append(item)
        if len(values) > 1:
            conflicts.append({
                'claim_key': key,
                'values': [
                    {'value': value, 'evidence_ids': [x['evidence_id'] for x in items],
                     'source_ids': sorted({x['source_id'] for x in items if x['source_id'] is not None})}
                    for value, items in values.items()
                ],
            })

    independent = len(source_ids)
    diversity = min(1.0, independent / 3) * 0.7 + min(1.0, len(domains) / 3) * 0.3
    conflict_penalty = min(0.35, 0.10 * len(conflicts))
    avg_quality = (sum(x['source_trust'] * 0.65 + x['freshness'] * 0.35 for x in rows) / len(rows)) if rows else 0.0
    score = max(0.0, min(1.0, avg_quality * 0.70 + diversity * 0.30 - conflict_penalty))
    return {
        'score': round(score, 4),
        'evidence_count': len(rows),
        'independent_sources': independent,
        'independent_domains': len(domains),
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
        'evidence': rows,
    }


def verification_history(db: Session, entity_type: str, entity_id: int) -> dict:
    rows = db.query(Verification).filter(
        Verification.entity_type == entity_type,
        Verification.entity_id == entity_id,
    ).order_by(Verification.created_at.asc()).all()
    timeline = [
        {'id': r.id, 'status': r.status, 'reviewer': r.reviewer, 'created_at': r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]
    changes = sum(1 for a, b in zip(timeline, timeline[1:]) if a['status'] != b['status'])
    return {'current': timeline[-1]['status'] if timeline else None, 'changes': changes, 'timeline': timeline}


def opportunity_source_intelligence(db: Session, op) -> dict:
    from ..models import Customer, Manufacturer, Demand
    entities = [
        ('customer', op.customer_id, db.get(Customer, op.customer_id)),
        ('manufacturer', op.manufacturer_id, db.get(Manufacturer, op.manufacturer_id)),
    ]
    if op.demand_id:
        entities.append(('demand', op.demand_id, db.get(Demand, op.demand_id)))

    chains = {}
    all_sources = set(); all_domains = set(); all_conflicts = []
    for et, eid, entity in entities:
        chain = evidence_chain(db, et, eid)
        hist = verification_history(db, et, eid)
        chains[et] = {'entity_id': eid, 'verification': getattr(entity, 'verification_status', None) if entity else None,
                       'chain': chain, 'history': hist}
        all_sources.update(x['source_id'] for x in chain['evidence'] if x['source_id'] is not None)
        all_domains.update(x['domain'] for x in chain['evidence'] if x['domain'])
        for c in chain['conflicts']:
            all_conflicts.append({'entity_type': et, **c})

    trust_rows = db.query(SourceTrust).filter(SourceTrust.source_id.in_(list(all_sources))).all() if all_sources else []
    avg_trust = sum(x.overall_score for x in trust_rows) / len(trust_rows) if trust_rows else 0.0
    diversity = min(100.0, 70.0 * min(1.0, len(all_sources) / 3) + 30.0 * min(1.0, len(all_domains) / 3))
    conflict_penalty = min(35.0, 10.0 * len(all_conflicts))
    evidence_scores = [v['chain']['score'] * 100 for v in chains.values() if v['chain']['evidence_count']]
    chain_score = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.0
    overall = round(max(0.0, min(100.0, 0.50 * chain_score + 0.30 * diversity + 0.20 * avg_trust * 100 - conflict_penalty)), 2)
    status = 'Strong' if overall >= 80 and not all_conflicts else ('Review' if overall >= 55 else 'Weak')
    return {
        'opportunity_id': op.id,
        'overall_score': overall,
        'status': status,
        'independent_sources': len(all_sources),
        'independent_domains': len(all_domains),
        'source_diversity_score': round(diversity, 2),
        'average_source_trust': round(avg_trust, 4),
        'conflict_count': len(all_conflicts),
        'conflicts': all_conflicts,
        'entities': chains,
        'recommendations': _recommendations(overall, all_conflicts, len(all_sources), len(all_domains)),
    }


def _recommendations(score, conflicts, sources, domains):
    out = []
    if conflicts:
        out.append({'priority': 'high', 'action': 'Resolve source conflicts', 'reason': 'منابع درباره حداقل یک ادعا اطلاعات متعارض دارند.'})
    if sources < 2:
        out.append({'priority': 'high', 'action': 'Add independent source', 'reason': 'برای افزایش corroboration حداقل دو منبع مستقل لازم است.'})
    if domains < 2:
        out.append({'priority': 'medium', 'action': 'Diversify domains', 'reason': 'منابع از دامنه‌های مستقل کافی نیستند.'})
    if score < 55:
        out.append({'priority': 'high', 'action': 'Manual verification', 'reason': 'زنجیره شواهد هنوز ضعیف است.'})
    return out
