from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import get_settings
settings=get_settings()
from ..models import TradeOutcomeFeedback
from ..services.request_guard import auth, serialize
from ..services.closed_loop import summarize_actor
from ..schemas import SupplierIn, BuyerIn, CommercialFactIn, FXRateIn, AIInferenceIn

router = APIRouter()

@router.get('/api/intelligence/trade-feedback')
def list_trade_feedback(request: Request, transaction_id: int|None=None, product_id: int|None=None, db: Session=Depends(get_db)):
    auth(request, db)
    q=db.query(TradeOutcomeFeedback)
    if transaction_id is not None: q=q.filter(TradeOutcomeFeedback.transaction_id==transaction_id)
    if product_id is not None: q=q.filter(TradeOutcomeFeedback.product_id==product_id)
    return [serialize(x) for x in q.order_by(TradeOutcomeFeedback.observed_at.desc()).limit(500).all()]

@router.get('/api/intelligence/actors/{actor_type}/{actor_id}')
def actor_intelligence(actor_type: str, actor_id: int, request: Request, db: Session=Depends(get_db)):
    auth(request, db)
    if actor_type == 'customer': return summarize_actor(db, customer_id=actor_id)
    if actor_type == 'manufacturer': return summarize_actor(db, manufacturer_id=actor_id)
    from fastapi import HTTPException
    raise HTTPException(400, 'نوع بازیگر معتبر نیست.')

@router.get('/api/intelligence/freshness')
def freshness_status(request: Request, kind: str='signals', limit: int=200, db: Session=Depends(get_db)):
    auth(request, db)
    from ..models import SourceSignal, Demand
    model = Demand if kind == 'demands' else SourceSignal
    rows = db.query(model).order_by(model.observed_at.desc().nullslast(), model.created_at.desc()).limit(min(max(limit,1),500)).all()
    return [serialize(x) for x in rows]

@router.get('/api/intelligence/entities/{entity_type}/{entity_id}/candidates')
def entity_candidates(entity_type: str, entity_id: int, request: Request, limit: int=20, db: Session=Depends(get_db)):
    auth(request, db)
    from ..services.entity_resolution import find_candidates
    if entity_type not in ('customer','manufacturer'):
        from fastapi import HTTPException
        raise HTTPException(400,'نوع موجودیت معتبر نیست.')
    return find_candidates(db, entity_type, entity_id, min(max(limit,1),50))

@router.post('/api/intelligence/entities/{entity_type}/{entity_id}/links/{other_type}/{other_id}')
def create_entity_link(entity_type: str, entity_id: int, other_type: str, other_id: int, request: Request, db: Session=Depends(get_db)):
    auth(request, db)
    from ..services.entity_resolution import find_candidates, entity_record
    from ..models import EntityLink
    candidates=find_candidates(db, entity_type, entity_id, 50)
    match=next((x for x in candidates if x['entity']['entity_type']==other_type and x['entity']['entity_id']==other_id),None)
    if not match:
        from fastapi import HTTPException
        raise HTTPException(400,'موجودیت دوم در مجموعه نامزدهای محافظه‌کارانه یافت نشد.')
    existing=db.query(EntityLink).filter_by(left_type=entity_type,left_id=entity_id,right_type=other_type,right_id=other_id).first()
    if existing: return serialize(existing)
    link=EntityLink(left_type=entity_type,left_id=entity_id,right_type=other_type,right_id=other_id,relation='confirmed_match',score=match['score'],reasons=match['reasons'],evidence={'candidate':match},reviewed=True)
    db.add(link); db.commit(); db.refresh(link); return serialize(link)

@router.post('/api/discovery/jobs')
def create_discovery_job(data: dict, request: Request, db: Session=Depends(get_db)):
    admin=auth(request,db)
    from ..services.job_queue import create_job
    from ..services.multi_market import resolve_market
    if 'product' in data:
        market_name=str(data.get('market') or settings.default_market_name or '').strip()
        if not market_name: raise HTTPException(400,'بازار باید به‌صورت مبدأ → مقصد مشخص شود.')
        if not resolve_market(db,market_name,allow_create=False): raise HTTPException(400,'بازار انتخاب‌شده وجود ندارد.')
        payload={k:data.get(k) for k in ('product','market','max_results','sources','query_terms','domains') if k in data}
        job_type='external_discovery'
        budget=min(max(int(settings.discovery_request_budget),1),500)
        retries=settings.discovery_max_retries
    else:
        job_type=str(data.get('job_type') or 'external_discovery')
        payload=data.get('payload') or {}
        budget=min(max(int(data.get('request_budget',50)),1),500)
        retries=min(max(int(data.get('max_retries',3)),0),10)
    job=create_job(db,job_type,payload,budget,retries,admin.id); db.commit(); db.refresh(job)
    return serialize(job)

@router.post('/api/discovery/jobs/{job_id}/run')
async def run_discovery_job(job_id:int, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    from ..models import DiscoveryJob
    from ..routers.remaining import _run_external_discovery
    from ..schemas import ExternalDiscoveryIn
    job=db.get(DiscoveryJob,job_id)
    if not job: raise HTTPException(404,'وظیفه پیدا نشد.')
    if job.status not in ('queued','failed'): raise HTTPException(409,'این وظیفه قابل اجرا نیست.')
    if job.created_by not in (None,admin.id) and admin.role!='Super Admin': raise HTTPException(403,'دسترسی به این وظیفه مجاز نیست.')
    if job.job_type!='external_discovery': raise HTTPException(400,'نوع این وظیفه توسط این اجراکننده پشتیبانی نمی‌شود.')
    return await _run_external_discovery(ExternalDiscoveryIn(**job.payload),request,db,job,admin)

@router.get('/api/discovery/jobs')
def list_discovery_jobs(request: Request, status: str|None=None, limit: int=50, db: Session=Depends(get_db)):
    admin=auth(request,db)
    from ..models import DiscoveryJob
    q=db.query(DiscoveryJob)
    if admin.role != 'Super Admin':
        q=q.filter(DiscoveryJob.created_by == admin.id)
    if status: q=q.filter(DiscoveryJob.status==status)
    return [serialize(x) for x in q.order_by(DiscoveryJob.created_at.desc()).limit(min(max(limit,1),200)).all()]

@router.post('/api/discovery/jobs/claim')
def claim_discovery_job(request: Request, db: Session=Depends(get_db)):
    auth(request,db)
    from ..services.job_queue import claim_next
    job=claim_next(db)
    if not job: return {'status':'empty'}
    db.commit(); db.refresh(job); return serialize(job)

@router.post('/api/discovery/jobs/{job_id}/complete')
def complete_discovery_job(job_id:int, data:dict, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    from ..models import DiscoveryJob
    from ..services.job_queue import finish_job, can_access_job
    job=db.get(DiscoveryJob,job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(404,'وظیفه پیدا نشد.')
    if not can_access_job(job, admin):
        raise HTTPException(403,'اجازه تکمیل این وظیفه را ندارید.')
    status=str(data.get('status') or 'completed')
    if status not in ('completed','failed','cancelled'):
        from fastapi import HTTPException
        raise HTTPException(400,'وضعیت وظیفه معتبر نیست.')
    finish_job(db,job,status,data.get('result') or {},data.get('error')); db.commit(); db.refresh(job); return serialize(job)

@router.get('/api/discovery/cache')
def search_cache_status(request: Request, source: str|None=None, limit:int=100, db:Session=Depends(get_db)):
    auth(request,db)
    from ..models import SearchCache
    from datetime import datetime, timezone
    q=db.query(SearchCache).filter(SearchCache.expires_at>datetime.now(timezone.utc))
    if source: q=q.filter(SearchCache.source==source)
    return [serialize(x) for x in q.order_by(SearchCache.updated_at.desc()).limit(min(max(limit,1),200)).all()]

# V24.18 intelligence integrity: canonical actors, commercial facts, FX and AI provenance
@router.get('/api/intelligence/suppliers')
def list_suppliers(request: Request, country: str|None=None, q: str|None=None, limit: int=100, db: Session=Depends(get_db)):
    auth(request, db)
    from ..models import Supplier
    query=db.query(Supplier).filter(Supplier.is_archived==False)
    if country: query=query.filter(Supplier.country==country)
    if q: query=query.filter(Supplier.canonical_name.ilike(f'%{q.strip()}%'))
    rows=query.order_by(Supplier.trust_score.desc(), Supplier.updated_at.desc()).limit(min(max(limit,1),500)).all()
    return [serialize(x) for x in rows]

@router.post('/api/intelligence/suppliers')
def create_supplier(data: SupplierIn, request: Request, db: Session=Depends(get_db)):
    admin=auth(request, db)
    from ..models import Supplier, AuditLog
    payload=data.model_dump()
    key=payload.get('canonical_key') or '|'.join(str(payload.get(x) or '').strip().lower() for x in ('canonical_name','country','city','phone','website'))
    existing=db.query(Supplier).filter(Supplier.canonical_key==key).first()
    if existing: return {'status':'existing','item':serialize(existing)}
    payload['canonical_key']=key
    row=Supplier(**payload)
    db.add(row); db.flush()
    db.add(AuditLog(admin_id=admin.id,action='supplier_created',entity_type='supplier',entity_id=row.id,details={'canonical_key':key}))
    db.commit(); db.refresh(row)
    return {'status':'created','item':serialize(row)}

@router.get('/api/intelligence/buyers')
def list_buyers(request: Request, country: str|None=None, q: str|None=None, limit: int=100, db: Session=Depends(get_db)):
    auth(request, db)
    from ..models import Buyer
    query=db.query(Buyer).filter(Buyer.is_archived==False)
    if country: query=query.filter(Buyer.country==country)
    if q: query=query.filter(Buyer.canonical_name.ilike(f'%{q.strip()}%'))
    rows=query.order_by(Buyer.reliability_score.desc(), Buyer.updated_at.desc()).limit(min(max(limit,1),500)).all()
    return [serialize(x) for x in rows]

@router.post('/api/intelligence/buyers')
def create_buyer(data: BuyerIn, request: Request, db: Session=Depends(get_db)):
    admin=auth(request, db)
    from ..models import Buyer, AuditLog
    payload=data.model_dump()
    key=payload.get('canonical_key') or '|'.join(str(payload.get(x) or '').strip().lower() for x in ('canonical_name','country','city','phone','website'))
    existing=db.query(Buyer).filter(Buyer.canonical_key==key).first()
    if existing: return {'status':'existing','item':serialize(existing)}
    payload['canonical_key']=key
    row=Buyer(**payload)
    db.add(row); db.flush()
    db.add(AuditLog(admin_id=admin.id,action='buyer_created',entity_type='buyer',entity_id=row.id,details={'canonical_key':key}))
    db.commit(); db.refresh(row)
    return {'status':'created','item':serialize(row)}

@router.get('/api/intelligence/commercial-facts')
def list_commercial_facts(request: Request, entity_type: str|None=None, entity_id: int|None=None, fact_type: str|None=None, limit: int=200, db: Session=Depends(get_db)):
    auth(request, db)
    from ..models import CommercialFact
    q=db.query(CommercialFact)
    if entity_type: q=q.filter(CommercialFact.entity_type==entity_type)
    if entity_id is not None: q=q.filter(CommercialFact.entity_id==entity_id)
    if fact_type: q=q.filter(CommercialFact.fact_type==fact_type)
    return [serialize(x) for x in q.order_by(CommercialFact.observed_at.desc()).limit(min(max(limit,1),500)).all()]

@router.post('/api/intelligence/commercial-facts')
def create_commercial_fact(data: CommercialFactIn, request: Request, db: Session=Depends(get_db)):
    admin=auth(request, db)
    from ..models import CommercialFact, SourceSignal, VerificationEvidence, AuditLog
    payload=data.model_dump()
    if payload['source_signal_id'] is not None and not db.get(SourceSignal,payload['source_signal_id']):
        raise HTTPException(422,'SourceSignal معتبر نیست.')
    if payload['evidence_id'] is not None and not db.get(VerificationEvidence,payload['evidence_id']):
        raise HTTPException(422,'Evidence معتبر نیست.')
    if payload['evidence_id'] is None and payload['source_signal_id'] is None:
        raise HTTPException(422,'Commercial Fact باید حداقل یک منبع شواهد یا SourceSignal داشته باشد.')
    payload['observed_at']=payload['observed_at'] or __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    row=CommercialFact(**payload); db.add(row); db.flush()
    db.add(AuditLog(admin_id=admin.id,action='commercial_fact_created',entity_type=payload['entity_type'],entity_id=payload['entity_id'],details={'fact_type':payload['fact_type'],'fact_id':row.id}))
    db.commit(); db.refresh(row)
    return serialize(row)

@router.get('/api/intelligence/fx-rates/latest')
def latest_fx_rate(request: Request, base_currency: str, quote_currency: str, db: Session=Depends(get_db)):
    auth(request, db)
    from ..models import FXRate
    from datetime import datetime, timezone
    now=datetime.now(timezone.utc)
    row=db.query(FXRate).filter(FXRate.base_currency==base_currency.upper(), FXRate.quote_currency==quote_currency.upper(), FXRate.status!='Rejected', (FXRate.expires_at.is_(None) | (FXRate.expires_at>=now))).order_by(FXRate.observed_at.desc()).first()
    if not row: raise HTTPException(404,'نرخ ارز معتبر و منقضی‌نشده پیدا نشد.')
    return serialize(row)

@router.post('/api/intelligence/fx-rates')
def create_fx_rate(data: FXRateIn, request: Request, db: Session=Depends(get_db)):
    admin=auth(request, db)
    from ..models import FXRate, Source, AuditLog
    payload=data.model_dump()
    if payload['source_id'] is None and not payload['source_url']:
        raise HTTPException(422,'FX Rate بدون منبع قابل ثبت نیست.')
    if payload['source_id'] is not None and not db.get(Source,payload['source_id']):
        raise HTTPException(422,'Source معتبر نیست.')
    from datetime import datetime, timezone
    payload['base_currency']=payload['base_currency'].upper(); payload['quote_currency']=payload['quote_currency'].upper(); payload['observed_at']=payload['observed_at'] or datetime.now(timezone.utc)
    row=FXRate(**payload); db.add(row); db.flush()
    db.add(AuditLog(admin_id=admin.id,action='fx_rate_created',entity_type='fx_rate',entity_id=row.id,details={'pair':f"{row.base_currency}/{row.quote_currency}"}))
    db.commit(); db.refresh(row)
    return serialize(row)

@router.post('/api/intelligence/ai-inferences')
def create_ai_inference(data: AIInferenceIn, request: Request, db: Session=Depends(get_db)):
    admin=auth(request, db)
    from ..models import AIInference, VerificationEvidence, AuditLog
    payload=data.model_dump()
    missing=[eid for eid in payload['evidence_ids'] if not db.get(VerificationEvidence,eid)]
    if missing: raise HTTPException(422,detail={'message':'Evidence ID نامعتبر است.','missing':missing})
    from datetime import datetime, timezone
    payload['generated_at']=payload['generated_at'] or datetime.now(timezone.utc)
    row=AIInference(**payload); db.add(row); db.flush()
    db.add(AuditLog(admin_id=admin.id,action='ai_inference_recorded',entity_type='ai_inference',entity_id=row.id,details={'task_type':row.task_type,'evidence_count':len(row.evidence_ids)}))
    db.commit(); db.refresh(row)
    return serialize(row)
