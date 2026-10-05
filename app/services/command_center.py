from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models.models import Opportunity, OpportunityAction, AlertEvent, Manufacturer, Customer, Demand, Product, SupplierQuote, CommercialOffer, LogisticsScenario, MarketPriceBenchmark, Market
from .opportunity_health import calculate_opportunity_health
from .data_quality import opportunity_data_quality

OPEN_STAGES = {'Discovered','Verified','Qualified','RFQ Sent','Supplier Quoted','Logistics Priced','Commercial Offer','Negotiation'}

def _now(): return datetime.now(timezone.utc)

def _active_query(db, product_id=None, market=None, stage=None):
    q = db.query(Opportunity).filter(Opportunity.is_archived == False)
    if product_id:
        q = q.filter(Opportunity.product_id == product_id)
    if stage:
        q = q.filter(Opportunity.opportunity_stage == stage)
    if market:
        exact=db.query(Market.id).filter(Market.name==market).scalar()
        if exact:
            q=q.filter(Opportunity.market_id==exact)
            return q
        # Market scope is represented by the manufacturer source country and customer target country.
        parts = [x.strip() for x in market.split('→', 1)] if '→' in market else []
        if len(parts) == 2:
            mf = db.query(Manufacturer.id).filter(Manufacturer.country == parts[0]).subquery()
            cu = db.query(Customer.id).filter(Customer.country == parts[1]).subquery()
            q = q.filter(Opportunity.manufacturer_id.in_(mf), Opportunity.customer_id.in_(cu))
        else:
            q = q.join(Customer, Customer.id == Opportunity.customer_id).filter(Customer.country == market)
    return q

def _stage_counts(rows):
    out = {s:0 for s in ['Discovered','Verified','Qualified','RFQ Sent','Supplier Quoted','Logistics Priced','Commercial Offer','Negotiation','Won','Lost']}
    for op in rows: out[op.opportunity_stage] = out.get(op.opportunity_stage,0) + 1
    return out

def _action_state(db, op_ids, now):
    if not op_ids: return {'open':0,'overdue':0,'due_24h':0}
    rows = db.query(OpportunityAction).filter(OpportunityAction.opportunity_id.in_(op_ids), OpportunityAction.status.in_(['Planned','In Progress'])).all()
    overdue = due = 0
    for a in rows:
        if a.due_at:
            dt = a.due_at if a.due_at.tzinfo else a.due_at.replace(tzinfo=timezone.utc)
            if dt < now: overdue += 1
            elif (dt-now).total_seconds() <= 86400: due += 1
    return {'open':len(rows),'overdue':overdue,'due_24h':due}

def command_center_summary(db: Session, product_id=None, market=None, stage=None):
    rows = _active_query(db, product_id, market, stage).all()
    now = _now(); ids=[x.id for x in rows]
    open_rows=[x for x in rows if x.opportunity_stage in OPEN_STAGES]
    actions=_action_state(db, ids, now)
    alert_q=db.query(AlertEvent).filter(AlertEvent.opportunity_id.in_(ids), AlertEvent.status.in_(['New','Acknowledged'])) if ids else None
    alerts=alert_q.all() if alert_q is not None else []
    severity={s:sum(1 for a in alerts if a.severity==s) for s in ['critical','high','medium','low']}
    # Watchtower uses high/medium today; critical remains supported for future alert types.
    at_risk=stale=blocked=0; health_counts={'Healthy':0,'Watch':0,'At Risk':0,'Closed':0}; quality_status={'Ready':0,'Warning':0,'Blocked':0}
    rows_health=[]
    for op in open_rows:
        h=calculate_opportunity_health(db,op)
        q=opportunity_data_quality(db,op)
        hs=h.get('status','Watch'); health_counts[hs]=health_counts.get(hs,0)+1
        if hs=='At Risk': at_risk += 1
        if q.get('status')=='Blocked': blocked += 1
        quality_status[q.get('status','Warning')] = quality_status.get(q.get('status','Warning'),0)+1
        age=(now-(op.stage_updated_at if op.stage_updated_at.tzinfo else op.stage_updated_at.replace(tzinfo=timezone.utc))).total_seconds()/86400
        if age >= 7: stale += 1
        rows_health.append((op,h,q,age))
    verified=sum(1 for op in rows if op.verification_status=='Verified')
    partial=sum(1 for op in rows if op.verification_status=='Partially Verified')
    unverified=sum(1 for op in rows if op.verification_status=='Unverified')
    quotes=db.query(SupplierQuote).filter(SupplierQuote.opportunity_id.in_(ids)).count() if ids else 0
    offers=db.query(CommercialOffer).filter(CommercialOffer.opportunity_id.in_(ids)).count() if ids else 0
    routes=db.query(LogisticsScenario).filter(LogisticsScenario.opportunity_id.in_(ids), LogisticsScenario.is_active==True).count() if ids else 0
    benchmarks=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id.in_([x.product_id for x in rows])).count() if rows else 0
    demands=db.query(Demand).filter(Demand.id.in_([x.demand_id for x in rows if x.demand_id])).count() if rows else 0
    return {
        'generated_at': now.isoformat(), 'filters': {'product_id':product_id,'market':market,'stage':stage},
        'kpis': {'total_opportunities':len(rows),'open_opportunities':len(open_rows),'closed_opportunities':len(rows)-len(open_rows),
                 'at_risk':at_risk,'stale_7d':stale,'blocked_data_quality':blocked,'active_alerts':len(alerts),
                 'overdue_actions':actions['overdue'],'due_next_24h':actions['due_24h'],'supplier_quotes':quotes,
                 'commercial_offers':offers,'active_routes':routes,'benchmarks':benchmarks,'linked_demands':demands},
        'pipeline': _stage_counts(rows), 'health':health_counts, 'data_quality':quality_status,
        'verification': {'Verified':verified,'Partially Verified':partial,'Unverified':unverified},
        'alerts': {'total':len(alerts), **severity},
        'action_state': actions,
    }

def command_center_opportunities(db: Session, product_id=None, market=None, stage=None, severity=None, limit=50):
    rows = _active_query(db, product_id, market, stage).order_by(Opportunity.stage_updated_at.asc()).limit(min(limit,200)).all()
    now=_now(); ids=[x.id for x in rows]
    alert_rows=db.query(AlertEvent).filter(AlertEvent.opportunity_id.in_(ids),AlertEvent.status.in_(['New','Acknowledged'])).all() if ids else []
    byop={}
    for a in alert_rows:
        if severity and a.severity.lower()!=severity.lower(): continue
        byop.setdefault(a.opportunity_id,[]).append(a)
    items=[]
    for op in rows:
        h=calculate_opportunity_health(db,op); q=opportunity_data_quality(db,op)
        age=(now-(op.stage_updated_at if op.stage_updated_at.tzinfo else op.stage_updated_at.replace(tzinfo=timezone.utc))).total_seconds()/86400
        al=byop.get(op.id,[])
        if severity and not al: continue
        customer=db.get(Customer,op.customer_id); manufacturer=db.get(Manufacturer,op.manufacturer_id); product=db.get(Product,op.product_id)
        items.append({'opportunity_id':op.id,'product':product.name if product else None,'customer':customer.name if customer else None,
                      'manufacturer':manufacturer.name if manufacturer else None,'stage':op.opportunity_stage,'priority':op.priority,
                      'score':round(float(op.score or 0),1),'health_status':h.get('status'),'risk_index':round(float(h.get('risk_index',0)),1),
                      'data_quality_status':q.get('status'),'verification_status':op.verification_status,'stage_age_days':round(age,1),
                      'overdue_actions':h.get('counts',{}).get('overdue_actions',0),'alerts':[{'id':a.id,'type':a.alert_type,'severity':a.severity,'message':a.message} for a in al],
                      'next_action':op.next_action})
    items.sort(key=lambda x:(-max({'critical':4,'high':3,'medium':2,'low':1}.get(a['severity'],0) for a in x['alerts']) if x['alerts'] else 0, -x['overdue_actions'], -x['risk_index'], -x['stage_age_days']))
    return {'count':len(items),'items':items}

def command_center_alerts(db: Session, product_id=None, market=None, status='New', severity=None, limit=100):
    rows = _active_query(db, product_id, market).all(); ids=[x.id for x in rows]
    q=db.query(AlertEvent).filter(AlertEvent.opportunity_id.in_(ids), AlertEvent.status==status) if ids else None
    if q is None: return {'count':0,'items':[]}
    if severity: q=q.filter(AlertEvent.severity==severity)
    alerts=q.order_by(AlertEvent.last_seen_at.desc()).limit(min(limit,200)).all()
    return {'count':len(alerts),'items':[{'id':a.id,'opportunity_id':a.opportunity_id,'alert_type':a.alert_type,'severity':a.severity,'status':a.status,'message':a.message,'reason':a.reason,'last_seen_at':a.last_seen_at.isoformat()} for a in alerts]}
