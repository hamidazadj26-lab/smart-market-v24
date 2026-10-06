from datetime import datetime, timezone

TERMINAL = {'Won', 'Lost'}


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))


def _days_since(dt, now):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400)


def _freshness(days):
    if days is None:
        return 35.0
    if days <= 1:
        return 100.0
    if days <= 3:
        return 85.0
    if days <= 7:
        return 65.0
    if days <= 14:
        return 45.0
    return 25.0


def calculate_opportunity_health(db, op, now=None):
    """Live, explainable opportunity health; no prediction of deal outcome."""
    now = now or datetime.now(timezone.utc)
    from ..models import Customer, Manufacturer, Demand, Product, OpportunityAction, SupplierQuote, LogisticsScenario, CommercialOffer, CommunicationLog, RFQDocument

    customer = db.get(Customer, op.customer_id)
    manufacturer = db.get(Manufacturer, op.manufacturer_id)
    demand = db.get(Demand, op.demand_id) if op.demand_id else None
    product = db.get(Product, op.product_id)
    open_actions = db.query(OpportunityAction).filter(OpportunityAction.opportunity_id == op.id, OpportunityAction.status.notin_(['Completed','Cancelled'])).count()
    overdue_actions = db.query(OpportunityAction).filter(OpportunityAction.opportunity_id == op.id, OpportunityAction.status.notin_(['Completed','Cancelled']), OpportunityAction.due_at.isnot(None), OpportunityAction.due_at < now).count()
    quotes = db.query(SupplierQuote).filter(SupplierQuote.opportunity_id == op.id).count()
    routes = db.query(LogisticsScenario).filter(LogisticsScenario.opportunity_id == op.id, LogisticsScenario.is_active == True).count()
    offers = db.query(CommercialOffer).filter(CommercialOffer.opportunity_id == op.id).count()
    outbound = db.query(CommunicationLog).filter(CommunicationLog.opportunity_id == op.id, CommunicationLog.direction == 'outbound').count()
    rfqs = db.query(RFQDocument).filter(RFQDocument.opportunity_id == op.id).count()

    verification = {'Verified':100.0,'Partially Verified':60.0,'Unverified':25.0,'Rejected':0.0}.get(op.verification_status,25.0)
    buyer_quality = _clamp((60 if customer else 0) + (20 if getattr(customer, 'phone', None) or getattr(customer, 'email', None) else 0) + (20 if getattr(customer, 'website', None) else 0))
    supplier_quality = _clamp((60 if manufacturer else 0) + (20 if getattr(manufacturer, 'phone', None) or getattr(manufacturer, 'email', None) else 0) + (20 if getattr(manufacturer, 'website', None) else 0))
    demand_quality = _clamp((50 if demand else 0) + (25 if demand and getattr(demand, 'quantity', None) else 0) + (25 if demand and getattr(demand, 'source_url', None) else 0))
    product_quality = 100.0 if product else 0.0
    execution = _clamp(min(100, quotes*30 + routes*25 + offers*30 + max(rfqs, outbound)*15))
    action_health = _clamp(100 - overdue_actions*25 + min(open_actions,3)*5)

    stage_days = _days_since(getattr(op, 'stage_updated_at', None), now) or 0.0
    stage_limits = {'Discovered':2,'Verified':3,'Qualified':3,'RFQ Sent':3,'Supplier Quoted':3,'Logistics Priced':3,'Commercial Offer':3,'Negotiation':5}
    limit = stage_limits.get(op.opportunity_stage)
    speed = _clamp(100 if not limit else 100 - max(0, stage_days-limit)*12)
    if op.opportunity_stage in TERMINAL:
        speed = 100.0
    due_health = 100.0
    if op.stage_due_at and op.opportunity_stage not in TERMINAL:
        due = op.stage_due_at if op.stage_due_at.tzinfo else op.stage_due_at.replace(tzinfo=timezone.utc)
        hours = (due-now).total_seconds()/3600
        due_health = 100.0 if hours > 24 else 70.0 if hours >= 0 else 20.0

    data_quality = round(0.25*verification + 0.2*buyer_quality + 0.2*supplier_quality + 0.2*demand_quality + 0.15*product_quality, 2)
    progress = round(0.55*execution + 0.25*action_health + 0.2*speed, 2)
    urgency = round(0.6*(100-due_health) + 0.4*max(0, 100-speed), 2)
    overall = round(0.45*data_quality + 0.35*progress + 0.20*(100-urgency), 2)
    risk = round(100-overall, 2)
    if op.opportunity_stage in TERMINAL:
        label = 'Closed'
    elif overall >= 80:
        label = 'Healthy'
    elif overall >= 60:
        label = 'Watch'
    else:
        label = 'At Risk'

    reasons=[]
    if verification < 60: reasons.append('اعتبارسنجی Buyer/Supplier ناکافی است.')
    if not demand: reasons.append('Demand مستقیم به فرصت متصل نیست.')
    if quotes == 0: reasons.append('هنوز Quote تأمین‌کننده ثبت نشده است.')
    if routes == 0 and op.opportunity_stage in {'Supplier Quoted','Logistics Priced','Commercial Offer','Negotiation'}: reasons.append('سناریوی حمل ثبت نشده است.')
    if overdue_actions: reasons.append(f'{overdue_actions} اقدام باز از موعد گذشته است.')
    if limit and stage_days > limit: reasons.append('مدت حضور در مرحله از زمان استاندارد عبور کرده است.')
    if not reasons: reasons.append('داده و اقدام فعلی برای ادامه فرآیند کافی است.')

    return {
        'opportunity_id': op.id, 'stage': op.opportunity_stage, 'label': label,
        'overall_health': overall, 'risk_index': risk, 'data_quality': data_quality,
        'execution_progress': progress, 'urgency': urgency, 'speed': round(speed,2),
        'verification_score': verification, 'buyer_quality': buyer_quality,
        'supplier_quality': supplier_quality, 'demand_quality': demand_quality,
        'counts': {'quotes':quotes,'routes':routes,'offers':offers,'rfqs':rfqs,'outbound_communications':outbound,'open_actions':open_actions,'overdue_actions':overdue_actions},
        'days_in_stage': round(stage_days,2), 'next_action': op.next_action,
        'reasons': reasons,
        'disclaimer': 'Health یک شاخص عملیاتی و کیفیت داده است و پیش‌بینی نتیجه معامله یا احتمال برد/باخت نیست.'
    }
