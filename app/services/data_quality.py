from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session


def _norm(v):
    return bool(v is not None and str(v).strip())


def _entity_quality(entity, required, recommended):
    if entity is None:
        return {'score': 0.0, 'status': 'Missing', 'missing': required[:], 'recommended_missing': recommended[:]}
    missing = [f for f in required if not _norm(getattr(entity, f, None))]
    rec = [f for f in recommended if not _norm(getattr(entity, f, None))]
    total = max(1, len(required) + len(recommended))
    score = round(100 * (total - len(missing) * 1.5 - len(rec) * 0.5) / total, 2)
    score = max(0.0, min(100.0, score))
    status = 'Complete' if not missing and not rec else ('Needs Review' if not missing else 'Incomplete')
    return {'score': score, 'status': status, 'missing': missing, 'recommended_missing': rec}


def _verification(db, entity_type, entity_id, entity):
    from ..models import VerificationEvidence
    evs = db.query(VerificationEvidence).filter(VerificationEvidence.entity_type == entity_type, VerificationEvidence.entity_id == entity_id).all()
    sources = set()
    for e in evs:
        if e.source_signal_id:
            sources.add(e.source_signal_id)
    status = getattr(entity, 'verification_status', 'Unverified') if entity else 'Missing'
    base = {'Verified': 100, 'Partially Verified': 60, 'Unverified': 25, 'Rejected': 0}.get(status, 25)
    corroboration = min(20, max(0, len(sources)-1) * 5)
    score = min(100, base + corroboration)
    return {'status': status, 'score': score, 'evidence_count': len(evs), 'independent_evidence': len(sources)}


def opportunity_data_quality(db: Session, op):
    from ..models import Customer, Manufacturer, Demand, Product, Source, MarketPriceBenchmark, SupplierQuote, LogisticsScenario, CommercialOffer, RFQDocument, CommunicationLog
    customer = db.get(Customer, op.customer_id)
    manufacturer = db.get(Manufacturer, op.manufacturer_id)
    demand = db.get(Demand, op.demand_id) if op.demand_id else None
    product = db.get(Product, op.product_id)

    customer_q = _entity_quality(customer, ['name','country'], ['city','address','phone','website','source_url'])
    supplier_q = _entity_quality(manufacturer, ['name','country'], ['city','address','phone','website','source_url','capacity_value'])
    demand_q = _entity_quality(demand, ['product_id','country'], ['quantity','unit','city','source_url','published_at','urgency'])
    product_q = _entity_quality(product, ['name'], ['category','unit'])

    ver = {
        'buyer': _verification(db, 'customer', op.customer_id, customer),
        'supplier': _verification(db, 'manufacturer', op.manufacturer_id, manufacturer),
        'demand': _verification(db, 'demand', op.demand_id, demand) if demand else {'status':'Missing','score':0,'evidence_count':0,'independent_evidence':0},
    }
    source_urls = sum(bool(getattr(x,'source_url',None)) for x in (customer, manufacturer, demand) if x)
    source_score = 100 if source_urls >= 3 else 70 if source_urls == 2 else 40 if source_urls == 1 else 0

    quotes = db.query(SupplierQuote).filter(SupplierQuote.opportunity_id == op.id).all()
    routes = db.query(LogisticsScenario).filter(LogisticsScenario.opportunity_id == op.id, LogisticsScenario.is_active == True).all()
    offers = db.query(CommercialOffer).filter(CommercialOffer.opportunity_id == op.id).all()
    rfqs = db.query(RFQDocument).filter(RFQDocument.opportunity_id == op.id).all()
    comms = db.query(CommunicationLog).filter(CommunicationLog.opportunity_id == op.id).all()
    benchmark = db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id == op.product_id).order_by(MarketPriceBenchmark.as_of.desc()).first()

    commercial = {
        'quotes': len(quotes), 'routes': len(routes), 'offers': len(offers), 'rfqs': len(rfqs), 'communications': len(comms),
        'benchmark_available': bool(benchmark),
        'quote_verified': sum(getattr(q,'status','') in ('Verified','Partially Verified') for q in quotes),
        'route_verified': sum(getattr(r,'verification_status','') in ('Verified','Partially Verified') for r in routes),
    }
    blockers=[]
    warnings=[]
    for key, q in [('buyer', customer_q), ('supplier', supplier_q), ('demand', demand_q)]:
        if q['status'] == 'Missing': blockers.append(f'{key}: entity missing')
        elif q['missing']: blockers.append(f'{key}: missing {", ".join(q["missing"])}')
        if q['recommended_missing']: warnings.append(f'{key}: recommended {", ".join(q["recommended_missing"])}')
    for key, v in ver.items():
        if v['status'] == 'Unverified': blockers.append(f'{key}: verification is Unverified')
        elif v['status'] == 'Rejected': blockers.append(f'{key}: verification is Rejected')
    if not quotes and op.opportunity_stage in {'RFQ Sent','Supplier Quoted','Logistics Priced','Commercial Offer','Negotiation'}: blockers.append('commercial: supplier quote missing')
    if not routes and op.opportunity_stage in {'Logistics Priced','Commercial Offer','Negotiation'}: blockers.append('logistics: route scenario missing')
    if not benchmark and op.opportunity_stage in {'Commercial Offer','Negotiation'}: warnings.append('market: benchmark unavailable')
    if not op.next_action: warnings.append('opportunity: next action missing')

    entity_scores=[customer_q['score'], supplier_q['score'], demand_q['score'], product_q['score']]
    verification_score=sum(v['score'] for v in ver.values())/len(ver)
    commercial_score=min(100, len(quotes)*30 + len(routes)*25 + len(offers)*30 + min(1, len(rfqs)+len(comms))*15)
    overall=round(0.45*(sum(entity_scores)/len(entity_scores)) + 0.25*verification_score + 0.15*source_score + 0.15*commercial_score,2)
    status='Ready' if not blockers and overall >= 80 else ('Needs Review' if len(blockers) <= 2 else 'Blocked')
    return {
        'opportunity_id': op.id, 'stage': op.opportunity_stage, 'overall_score': overall, 'status': status,
        'entity_quality': {'buyer':customer_q,'supplier':supplier_q,'demand':demand_q,'product':product_q},
        'verification': ver, 'source_quality': {'score':source_score,'source_url_count':source_urls},
        'commercial_completeness': commercial, 'blockers': blockers, 'warnings': warnings,
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'gate': {'can_advance': not blockers, 'blocking_count':len(blockers), 'warning_count':len(warnings)},
    }
