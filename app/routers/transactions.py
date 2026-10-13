from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import *
from ..schemas import TransactionCreateIn, TransactionTransitionIn, TransactionOutcomeIn
from ..services.request_guard import auth, serialize
from ..transaction import transition, record_outcome

router = APIRouter()

@router.get('/api/transactions')
def list_transactions(request: Request, status: str|None=None, opportunity_id: int|None=None, db: Session=Depends(get_db)):
    auth(request, db)
    q=db.query(Transaction)
    if status: q=q.filter(Transaction.status==status)
    if opportunity_id is not None: q=q.filter(Transaction.opportunity_id==opportunity_id)
    return [serialize(x) for x in q.order_by(Transaction.created_at.desc()).limit(500).all()]

@router.get('/api/transactions/{transaction_id}')
def get_transaction(transaction_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    tx=db.get(Transaction,transaction_id)
    if not tx: raise HTTPException(404,'معامله پیدا نشد.')
    events=db.query(TransactionEvent).filter(TransactionEvent.transaction_id==tx.id).order_by(TransactionEvent.created_at.asc()).all()
    return {'transaction':serialize(tx),'events':[serialize(x) for x in events]}

@router.post('/api/opportunities/{opportunity_id}/transactions')
def create_transaction(opportunity_id:int, data:TransactionCreateIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    opp=db.get(Opportunity,opportunity_id)
    if not opp: raise HTTPException(404,'فرصت پیدا نشد.')
    if opp.is_archived: raise HTTPException(409,'فرصت بایگانی شده است.')
    existing=db.query(Transaction).filter(Transaction.opportunity_id==opportunity_id,Transaction.status.notin_(['Cancelled','Completed'])).first()
    if existing: raise HTTPException(409,'برای این فرصت یک معامله فعال وجود دارد.')
    offer=db.get(CommercialOffer,data.commercial_offer_id) if data.commercial_offer_id else None
    if offer and offer.opportunity_id != opportunity_id: raise HTTPException(400,'پیشنهاد تجاری متعلق به این فرصت نیست.')
    quantity=data.quantity if data.quantity is not None else (offer.quantity if offer else None)
    if quantity is None: raise HTTPException(400,'مقدار معامله باید مشخص باشد.')
    currency=data.currency or (offer.currency if offer else 'USD')
    unit=data.unit or (offer.unit if offer else 'kg')
    unit_price=data.agreed_unit_price if data.agreed_unit_price is not None else (offer.cif_unit_price if offer and offer.cif_unit_price else (offer.fob_unit_price if offer else None))
    total=data.agreed_total if data.agreed_total is not None else (unit_price*quantity if unit_price else None)
    tx=Transaction(opportunity_id=opportunity_id,market_id=opp.market_id,commercial_offer_id=offer.id if offer else None,customer_id=opp.customer_id,manufacturer_id=opp.manufacturer_id,product_id=opp.product_id,status='Draft',currency=currency,quantity=quantity,unit=unit,agreed_unit_price=unit_price,agreed_total=total,incoterm=data.incoterm or (offer.incoterm if offer else None),notes=data.notes,created_by=admin.id)
    db.add(tx); db.flush()
    db.add(TransactionEvent(transaction_id=tx.id,event_type='created',to_status='Draft',notes=data.notes,created_by=admin.id))
    db.add(AuditLog(admin_id=admin.id,action='transaction_created',entity_type='transaction',entity_id=tx.id,details={'opportunity_id':opportunity_id,'commercial_offer_id':tx.commercial_offer_id}))
    db.commit(); db.refresh(tx)
    return {'transaction':serialize(tx),'events':[serialize(x) for x in db.query(TransactionEvent).filter(TransactionEvent.transaction_id==tx.id).all()]}

@router.post('/api/transactions/{transaction_id}/transition')
def transition_transaction(transaction_id:int, data:TransactionTransitionIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); tx=db.get(Transaction,transaction_id)
    if not tx: raise HTTPException(404,'معامله پیدا نشد.')
    transition(db,tx,data.status,admin.id,data.notes,data.payload)
    db.add(AuditLog(admin_id=admin.id,action='transaction_status_changed',entity_type='transaction',entity_id=tx.id,details={'status':data.status,'notes':data.notes,'payload':data.payload}))
    db.commit(); db.refresh(tx)
    return serialize(tx)

@router.post('/api/transactions/{transaction_id}/outcome')
def transaction_outcome(transaction_id:int, data:TransactionOutcomeIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); tx=db.get(Transaction,transaction_id)
    if not tx: raise HTTPException(404,'معامله پیدا نشد.')
    record_outcome(db,tx,data,admin.id)
    db.add(AuditLog(admin_id=admin.id,action='transaction_outcome_recorded',entity_type='transaction',entity_id=tx.id,details=data.model_dump(exclude_unset=True)))
    db.commit(); db.refresh(tx)
    return {'transaction':serialize(tx),'events':[serialize(x) for x in db.query(TransactionEvent).filter(TransactionEvent.transaction_id==tx.id).order_by(TransactionEvent.created_at.asc()).all()]}
