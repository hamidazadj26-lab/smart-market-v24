from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from sqlalchemy.orm import Session

from ..models import Opportunity, VerificationEvidence, SourceSignal, Source, AuditLog, Customer, Manufacturer, Demand
from .source_evidence import _claim, _domain


def _dt(v):
    if not v:
        return None
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v


def _iso(v):
    return _dt(v).isoformat() if v else None


def _event_hash(payload: dict) -> str:
    import json
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return sha256(raw.encode()).hexdigest()


def _entities_for_op(db: Session, op: Opportunity):
    pairs = [
        ('customer', op.customer_id, db.get(Customer, op.customer_id)),
        ('manufacturer', op.manufacturer_id, db.get(Manufacturer, op.manufacturer_id)),
    ]
    if op.demand_id:
        pairs.append(('demand', op.demand_id, db.get(Demand, op.demand_id)))
    return [(a, i, o) for a, i, o in pairs if o]


def _signal_context(db: Session, ev):
    sig = db.get(SourceSignal, ev.source_signal_id) if ev.source_signal_id else None
    src = db.get(Source, sig.source_id) if sig and sig.source_id else None
    url = ev.source_url or (sig.source_url if sig else None) or (src.base_url if src else None)
    return sig, src, _domain(url)


def detect_opportunity_changes(db: Session, op: Opportunity, days: int = 180, persist: bool = False, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=max(1, min(days, 3650)))
    events = []
    source_ids = set()
    domains = set()

    for entity_type, entity_id, entity in _entities_for_op(db, op):
        evs = db.query(VerificationEvidence).filter(
            VerificationEvidence.entity_type == entity_type,
            VerificationEvidence.entity_id == entity_id,
            VerificationEvidence.created_at >= start,
        ).order_by(VerificationEvidence.created_at.asc()).all()

        claim_history = defaultdict(list)
        signal_history = defaultdict(list)
        for ev in evs:
            sig, src, domain = _signal_context(db, ev)
            if src:
                source_ids.add(src.id)
            if domain:
                domains.add(domain)
            claim = _claim(ev)
            if claim:
                key, value = claim
                claim_history[key].append({
                    'value': value,
                    'evidence_id': ev.id,
                    'source_id': src.id if src else None,
                    'source_name': src.name if src else None,
                    'domain': domain,
                    'observed_at': _iso(getattr(sig, 'published_at', None) or getattr(sig, 'retrieved_at', None) or ev.created_at),
                    'created_at': _iso(ev.created_at),
                })
            if sig and sig.external_key:
                signal_history[(sig.source_id, sig.external_key)].append(sig)

        # Same claim changed over time.
        for key, rows in claim_history.items():
            previous = None
            for row in rows:
                if previous and row['value'] != previous['value']:
                    events.append({
                        'event_type': 'claim_changed',
                        'entity_type': entity_type,
                        'entity_id': entity_id,
                        'claim_key': key,
                        'old_value': previous['value'],
                        'new_value': row['value'],
                        'old_source_id': previous['source_id'],
                        'new_source_id': row['source_id'],
                        'old_domain': previous['domain'],
                        'new_domain': row['domain'],
                        'detected_at': row['created_at'],
                        'severity': 'high' if previous['source_id'] == row['source_id'] else 'medium',
                        'reason': 'A previously observed claim value changed.' if previous['source_id'] == row['source_id'] else 'Independent sources report different values over time.',
                    })
                previous = row

        # Cross-source disagreement among latest claims.
        for key, rows in claim_history.items():
            latest_by_source = {}
            for row in rows:
                sid = row['source_id'] or f"evidence:{row['evidence_id']}"
                latest_by_source[sid] = row
            values = defaultdict(list)
            for row in latest_by_source.values():
                values[row['value']].append(row)
            if len(values) > 1:
                events.append({
                    'event_type': 'cross_source_conflict',
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'claim_key': key,
                    'values': [
                        {'value': value, 'source_ids': sorted({x['source_id'] for x in rows2 if x['source_id'] is not None}),
                         'domains': sorted({x['domain'] for x in rows2 if x['domain']})}
                        for value, rows2 in values.items()
                    ],
                    'detected_at': _iso(now),
                    'severity': 'high',
                    'reason': 'Latest evidence from independent sources disagrees.',
                })

        # Same external source record changed content.
        for (source_id, external_key), signals in signal_history.items():
            signals.sort(key=lambda x: _dt(x.retrieved_at or x.created_at))
            prev = None
            for sig in signals:
                if prev and sig.content_hash and prev.content_hash and sig.content_hash != prev.content_hash:
                    events.append({
                        'event_type': 'source_content_changed',
                        'entity_type': entity_type,
                        'entity_id': entity_id,
                        'source_id': source_id,
                        'external_key': external_key,
                        'old_hash': prev.content_hash,
                        'new_hash': sig.content_hash,
                        'detected_at': _iso(sig.retrieved_at or sig.created_at),
                        'severity': 'medium',
                        'reason': 'The same source record changed content between retrievals.',
                    })
                prev = sig

    # De-duplicate semantically identical events.
    unique = {}
    for event in events:
        h = _event_hash({k: v for k, v in event.items() if k not in {'detected_at'}})
        event['event_hash'] = h
        unique[h] = event
    events = sorted(unique.values(), key=lambda x: (x.get('severity') != 'high', x.get('detected_at') or ''), reverse=False)

    persisted = 0
    if persist:
        existing = {x.details.get('event_hash') for x in db.query(AuditLog).filter(
            AuditLog.action == 'source_change_detected', AuditLog.entity_type == 'opportunity', AuditLog.entity_id == op.id
        ).all() if isinstance(x.details, dict)}
        for event in events:
            if event['event_hash'] in existing:
                continue
            db.add(AuditLog(action='source_change_detected', entity_type='opportunity', entity_id=op.id,
                             details=event))
            persisted += 1
        if persisted:
            db.commit()

    high = sum(1 for x in events if x.get('severity') == 'high')
    medium = sum(1 for x in events if x.get('severity') == 'medium')
    status = 'Critical Review' if high >= 2 else ('Review' if events else 'No Material Change')
    return {
        'opportunity_id': op.id,
        'window_days': days,
        'status': status,
        'event_count': len(events),
        'high_events': high,
        'medium_events': medium,
        'independent_sources': len(source_ids),
        'independent_domains': len(domains),
        'events': events,
        'persisted_events': persisted,
        'recommendations': _recommendations(events),
    }


def _recommendations(events):
    out = []
    if any(x['event_type'] == 'cross_source_conflict' for x in events):
        out.append({'priority': 'high', 'action': 'Resolve cross-source conflict', 'reason': 'آخرین شواهد مستقل درباره حداقل یک ادعا هم‌نظر نیستند.'})
    if any(x['event_type'] == 'claim_changed' for x in events):
        out.append({'priority': 'high', 'action': 'Re-verify changed claim', 'reason': 'یک مقدار قبلاً مشاهده‌شده تغییر کرده است.'})
    if any(x['event_type'] == 'source_content_changed' for x in events):
        out.append({'priority': 'medium', 'action': 'Review updated source record', 'reason': 'محتوای یک رکورد منبع در retrieval جدید تغییر کرده است.'})
    return out
