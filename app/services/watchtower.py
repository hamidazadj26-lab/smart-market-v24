from datetime import datetime, timezone, timedelta
import hashlib, json
from sqlalchemy.orm import Session
from ..models.models import Opportunity, AlertEvent
from .opportunity_health import calculate_opportunity_health
from .data_quality import opportunity_data_quality
from .temporal_intelligence import opportunity_temporal_intelligence
from .change_detection import detect_opportunity_changes
from .automation import build_automation_plan


def _now(): return datetime.now(timezone.utc)

def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

def _alert(severity, alert_type, message, reason, op, payload=None):
    payload = payload or {}
    key = _hash({'opportunity_id': op.id, 'type': alert_type, 'severity': severity, 'message': message, 'reason': reason, 'payload': payload})
    return {'dedup_key': key, 'opportunity_id': op.id, 'severity': severity, 'alert_type': alert_type,
            'message': message, 'reason': reason, 'payload': payload}

def evaluate_opportunity(db: Session, op: Opportunity, days=180):
    alerts=[]
    if op.is_archived or op.opportunity_stage in {'Won','Lost'}: return alerts
    h=calculate_opportunity_health(db,op)
    q=opportunity_data_quality(db,op)
    t=opportunity_temporal_intelligence(db,op,max(7,min(days,3650)))
    c=detect_opportunity_changes(db,op,days=max(7,min(days,3650)),persist=False)
    if h['status']=='At Risk' or h.get('risk_index',0)>=65:
        alerts.append(_alert('high','opportunity_at_risk','Opportunity نیازمند توجه فوری است.','Health در وضعیت At Risk.',op,{'health':h.get('risk_index',0)}))
    if h.get('overdue_actions',h.get('counts',{}).get('overdue_actions',0))>0:
        alerts.append(_alert('high','overdue_action','اقدام پیگیری معوق وجود دارد.','Action Center دارای اقدام overdue است.',op,{'count':h.get('overdue_actions',h.get('counts',{}).get('overdue_actions',0))}))
    if not q['gate']['can_advance']:
        alerts.append(_alert('high','data_quality_blocker','Opportunity در Data Quality Gate متوقف شده است.','اطلاعات لازم برای عبور از مرحله کامل نیست.',op,{'blockers':q['blockers']}))
    if t['direction']=='Deteriorating':
        alerts.append(_alert('high','temporal_deterioration','شاخص زمانی Opportunity در حال تضعیف است.','Temporal Intelligence روند منفی یا کهنگی معنادار نشان می‌دهد.',op,{'temporal_score':t['temporal_score'],'signals':t.get('signals',[])[:5]}))
    if t.get('benchmark',{}).get('freshness_score',100)<40:
        alerts.append(_alert('medium','stale_benchmark','Benchmark بازار قدیمی است.','Benchmark freshness پایین است.',op,{'freshness':t['benchmark'].get('freshness_score')}))
    if c.get('high_events',0)>0:
        alerts.append(_alert('high','source_change_high','تغییر مهم بین منابع شناسایی شده است.','حداقل یک Change Event با شدت بالا وجود دارد.',op,{'count':c['high_events'],'events':c.get('events',[])[:5]}))
    elif c.get('medium_events',0)>0:
        alerts.append(_alert('medium','source_change_medium','تغییر یا تعارض متوسط بین منابع شناسایی شده است.','Change Event با شدت متوسط وجود دارد.',op,{'count':c['medium_events'],'events':c.get('events',[])[:5]}))
    return alerts

def plan_watchtower(db: Session, days=180, limit=200):
    rows=db.query(Opportunity).filter(Opportunity.is_archived==False, Opportunity.opportunity_stage.notin_(['Won','Lost'])).order_by(Opportunity.stage_updated_at.asc()).limit(min(limit,500)).all()
    alerts=[]
    for op in rows: alerts.extend(evaluate_opportunity(db,op,days))
    return {'generated_at':_now().isoformat(),'opportunity_count':len(rows),'alert_count':len(alerts),'items':alerts}

def persist_alerts(db: Session, items, admin_id=None):
    created=[]; updated=[]
    for item in items:
        existing=db.query(AlertEvent).filter(AlertEvent.dedup_key==item['dedup_key'],AlertEvent.status.in_(['New','Acknowledged'])).first()
        if existing:
            existing.last_seen_at=_now(); existing.payload=item['payload']; updated.append(existing.id); continue
        row=AlertEvent(**item, status='New', first_seen_at=_now(), last_seen_at=_now(), created_by=admin_id)
        db.add(row); db.flush(); created.append(row.id)
    db.commit()
    return {'created_ids':created,'refreshed_ids':updated}
