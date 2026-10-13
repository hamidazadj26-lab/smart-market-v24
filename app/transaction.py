from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .models import Transaction, TransactionEvent, Opportunity, CommercialOffer, MarketPriceObservation, Market
from .services.closed_loop import record_trade_feedback

STATUSES = ['Draft','Confirmed','Payment Pending','Paid','Preparing','Shipped','In Transit','Delivered','Completed','Cancelled','Disputed']
TRANSITIONS = {
    'Draft': {'Confirmed','Cancelled'},
    'Confirmed': {'Payment Pending','Paid','Cancelled','Disputed'},
    'Payment Pending': {'Paid','Cancelled','Disputed'},
    'Paid': {'Preparing','Cancelled','Disputed'},
    'Preparing': {'Shipped','Cancelled','Disputed'},
    'Shipped': {'In Transit','Delivered','Disputed'},
    'In Transit': {'Delivered','Disputed'},
    'Delivered': {'Completed','Disputed'},
    'Completed': set(),
    'Cancelled': set(),
    'Disputed': {'Confirmed','Payment Pending','Paid','Cancelled','Completed'},
}

def now(): return datetime.now(timezone.utc)

def transition(db: Session, tx: Transaction, to_status: str, admin_id: int|None, notes: str|None=None, payload: dict|None=None):
    if to_status not in STATUSES:
        raise HTTPException(400, 'وضعیت معامله معتبر نیست.')
    if to_status != tx.status and to_status not in TRANSITIONS.get(tx.status, set()):
        raise HTTPException(409, f'انتقال معامله از {tx.status} به {to_status} مجاز نیست.')
    old = tx.status
    ts = now()
    tx.status = to_status
    if to_status == 'Confirmed': tx.confirmed_at = tx.confirmed_at or ts
    if to_status == 'Paid': tx.paid_at = tx.paid_at or ts; tx.payment_status='Paid'
    if to_status in {'Shipped','In Transit','Delivered'}: tx.logistics_status = to_status
    if to_status == 'Delivered': tx.delivered_at = tx.delivered_at or ts
    if to_status == 'Shipped': tx.shipped_at = tx.shipped_at or ts
    if to_status == 'Completed':
        tx.completed_at = tx.completed_at or ts
        tx.logistics_status = 'Completed'
    event = TransactionEvent(transaction_id=tx.id,event_type='status_changed',from_status=old,to_status=to_status,notes=notes,payload=payload or {},created_by=admin_id)
    db.add(event)
    return event

def record_outcome(db: Session, tx: Transaction, data, admin_id: int|None):
    values=data.model_dump(exclude_unset=True)
    for k in ('actual_quantity','actual_unit_price','actual_total','actual_freight','actual_delivery_days','notes'):
        if k in values: setattr(tx,k,values[k])
    tx.outcome = values.get('outcome') or tx.outcome or {}
    if tx.actual_total is None and tx.actual_quantity and tx.actual_unit_price:
        tx.actual_total = tx.actual_quantity * tx.actual_unit_price
    if tx.status != 'Completed': transition(db,tx,'Completed',admin_id,'Outcome recorded')
    if tx.actual_unit_price and tx.product_id:
        market_obj = db.get(Market, tx.market_id) if tx.market_id else None
        market = market_obj.name if market_obj else None
        if market:
            obs=MarketPriceObservation(product_id=tx.product_id,market=market,price=tx.actual_unit_price,currency=tx.currency,unit=tx.unit,incoterm=tx.incoterm,quantity=tx.actual_quantity or tx.quantity,observed_at=now(),verification_status='Partially Verified',confidence=0.8,notes=f'Observed from completed transaction #{tx.id}')
            db.add(obs)
    feedback = record_trade_feedback(db, tx, admin_id=admin_id)
    db.flush()
    db.add(TransactionEvent(transaction_id=tx.id,event_type='outcome_recorded',notes=data.notes,payload={**values,'feedback_id':feedback.id},created_by=admin_id))
