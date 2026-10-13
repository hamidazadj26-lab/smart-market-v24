from datetime import datetime, timezone, timedelta

STAGE_DEFAULT_DAYS = {
    'Discovered': 2, 'Verified': 3, 'Qualified': 3, 'RFQ Sent': 3,
    'Supplier Quoted': 3, 'Logistics Priced': 3, 'Commercial Offer': 3,
    'Negotiation': 5,
}
TERMINAL = {'Won','Lost'}

def now_utc():
    return datetime.now(timezone.utc)

def _open_actions(db, opportunity_id):
    from ..models import OpportunityAction
    return db.query(OpportunityAction).filter(
        OpportunityAction.opportunity_id == opportunity_id,
        OpportunityAction.status.notin_(['Completed','Cancelled'])
    ).all()

def _has_auto(db, opportunity_id, marker):
    from ..models import OpportunityAction
    return db.query(OpportunityAction).filter(
        OpportunityAction.opportunity_id == opportunity_id,
        OpportunityAction.status.notin_(['Completed','Cancelled']),
        OpportunityAction.subject.like(f'[AUTO:{marker}]%')
    ).first() is not None

def build_automation_plan(db, op, now=None):
    now = now or now_utc()
    if op.opportunity_stage in TERMINAL or op.is_archived:
        return []
    actions=[]
    open_actions=_open_actions(db, op.id)
    has_followup=any(a.action_type in {'follow_up','call','whatsapp','email','meeting'} for a in open_actions)
    if op.stage_due_at and op.stage_due_at < now and not _has_auto(db, op.id, 'OVERDUE'):
        actions.append({'marker':'OVERDUE','action_type':'follow_up','status':'Planned','subject':f'[AUTO:OVERDUE] پیگیری مرحله {op.opportunity_stage}','notes':f'مرحله {op.opportunity_stage} از موعد خود عبور کرده است.','due_at':now,'result':None})
    elif op.stage_due_at and now <= op.stage_due_at <= now + timedelta(hours=24) and not _has_auto(db, op.id, 'DUE24'):
        actions.append({'marker':'DUE24','action_type':'follow_up','status':'Planned','subject':f'[AUTO:DUE24] یادآوری موعد مرحله {op.opportunity_stage}','notes':'موعد مرحله طی 24 ساعت آینده است.','due_at':op.stage_due_at,'result':None})
    if op.next_action and not has_followup and not _has_auto(db, op.id, 'NEXT'):
        due=op.stage_due_at or (now + timedelta(days=1))
        actions.append({'marker':'NEXT','action_type':'follow_up','status':'Planned','subject':f'[AUTO:NEXT] {op.next_action[:180]}','notes':'این اقدام از next_action فرصت ایجاد شده است.','due_at':due,'result':None})
    if not op.stage_due_at:
        days=STAGE_DEFAULT_DAYS.get(op.opportunity_stage)
        if days and op.stage_updated_at and op.stage_updated_at + timedelta(days=days) < now and not _has_auto(db, op.id, 'STALE'):
            actions.append({'marker':'STALE','action_type':'follow_up','status':'Planned','subject':f'[AUTO:STALE] فرصت در مرحله {op.opportunity_stage} بدون موعد','notes':f'فرصت بیش از {days} روز در این مرحله مانده است.','due_at':now,'result':None})
    return actions

def run_automation(db, admin_id=None, opportunity_id=None, dry_run=False):
    from ..models import Opportunity, OpportunityAction, AuditLog
    q=db.query(Opportunity).filter(Opportunity.is_archived==False, Opportunity.opportunity_stage.notin_(list(TERMINAL)))
    if opportunity_id is not None:
        q=q.filter(Opportunity.id==opportunity_id)
    created=[]
    for op in q.order_by(Opportunity.stage_updated_at.asc()).all():
        for item in build_automation_plan(db, op):
            if dry_run:
                created.append({'opportunity_id':op.id,**item})
                continue
            payload={k:v for k,v in item.items() if k!='marker'}
            action=OpportunityAction(opportunity_id=op.id, created_by=admin_id, **payload)
            db.add(action); db.flush()
            db.add(AuditLog(admin_id=admin_id, action='automation_action_created', entity_type='opportunity_action', entity_id=action.id, details={'opportunity_id':op.id,'marker':item['marker']}))
            created.append({'opportunity_id':op.id,'action_id':action.id,'marker':item['marker']})
    if not dry_run:
        db.commit()
    return created
