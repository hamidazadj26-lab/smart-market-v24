"""Discovery and verification API routes extracted from the monolithic API."""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import *
from ..schemas import *
from ..security.auth import *
from ..services.rbac import audit, require_permission
from ..services.request_guard import auth, serialize
from ..discovery.engine import discover_from_signal, classify_signal
from ..verification.intelligence import canonical_key, evidence_score, update_candidate_trust, find_candidate_duplicates, merge_candidate

router = APIRouter(tags=["discovery", "verification"])

@router.get('/api/discovery/candidates')
def discovery_candidates(request:Request, db=Depends(get_db)):
    auth(request, db)
    return [serialize(x) for x in db.query(DiscoveryCandidate).filter(DiscoveryCandidate.is_archived==False).order_by(DiscoveryCandidate.confidence.desc()).all()]

@router.post('/api/discovery/run')
def discovery_run(data:DiscoveryRunIn, request:Request, db=Depends(get_db)):
    auth(request, db)
    signals=[]
    if data.signal_ids:
        signals.extend(db.query(SourceSignal).filter(SourceSignal.id.in_(data.signal_ids)).all())
    for text in data.texts:
        if not text.strip():
            continue
        sig=SourceSignal(raw_text=text.strip(), source_title='Manual Discovery', verification_status='Unverified', confidence=0.0)
        db.add(sig); db.flush(); signals.append(sig)
    results=[]
    for sig in signals:
        result=discover_from_signal(db, sig, requested_product=data.product)
        ext=result['extracted']
        candidate=DiscoveryCandidate(
            source_signal_id=sig.id, name=ext.get('company_name'), country=ext.get('country'), city=ext.get('city'),
            activity_type=ext.get('activity_type'), product_name=ext.get('product_name'), candidate_type=result['classification'],
            demand_likelihood=ext.get('demand_likelihood') or 0, confidence=ext.get('confidence') or 0, evidence=ext.get('evidence') or {}, status='Review', canonical_key=canonical_key(ext.get('company_name'), ext.get('country'), ext.get('city')), trust_score=ext.get('confidence') or 0
        )
        db.add(candidate); db.flush()
        results.append({'signal_id':sig.id,'candidate_id':candidate.id,**result})
    db.commit()
    return {'status':'ok','processed':len(signals),'results':results}

@router.post('/api/discovery/classify')
def discovery_classify(data:SignalIn, request:Request, db=Depends(get_db)):
    auth(request, db)
    ext=classify_signal(data.raw_text, source_name=data.source_title, requested_product=(data.normalized_payload or {}).get('requested_product'))
    return {'classification':ext.customer_type,'extracted':ext.__dict__}

@router.patch('/api/discovery/candidates/{candidate_id}')
def review_candidate(candidate_id:int, data:CandidateReviewIn, request:Request, db=Depends(get_db)):
    admin=auth(request, db)
    candidate=db.get(DiscoveryCandidate,candidate_id)
    if not candidate: raise HTTPException(404,'کاندید پیدا نشد.')
    candidate.status=data.status
    db.add(AuditLog(admin_id=admin.id, action='discovery_candidate_review', entity_type='discovery_candidate', entity_id=candidate_id, details={'status':data.status}))
    db.commit(); db.refresh(candidate)
    return serialize(candidate)

@router.post('/api/verify/{entity_type}/{entity_id}')
def verify_entity(entity_type:str,entity_id:int,data:VerifyIn,request:Request,db=Depends(get_db)):
    admin=auth(request,db)
    allowed={'manufacturer':Manufacturer,'customer':Customer,'demand':Demand,'signal':SourceSignal,'opportunity':Opportunity}
    if entity_type not in allowed: raise HTTPException(400,'نوع موجودیت برای تأیید معتبر نیست.')
    obj=db.get(allowed[entity_type],entity_id)
    if not obj: raise HTTPException(404,'رکورد پیدا نشد.')
    obj.verification_status=data.status
    if hasattr(obj,'verification_notes') and data.notes: obj.verification_notes=data.notes
    if data.status=='Verified' and hasattr(obj,'confidence'): obj.confidence=max(float(obj.confidence or 0),0.85)
    v=Verification(entity_type=entity_type,entity_id=entity_id,status=data.status,evidence=data.evidence,reviewer=data.reviewer or admin.username)
    db.add(v)
    if data.evidence:
        db.add(VerificationEvidence(entity_type=entity_type, entity_id=entity_id, evidence_type='manual_review', weight=1.0 if data.status=='Verified' else 0.5, excerpt=data.notes, source_url=data.evidence.get('source_url') if isinstance(data.evidence, dict) else None, details={'reviewer':data.reviewer or admin.username, **(data.evidence if isinstance(data.evidence, dict) else {})}))
    db.add(AuditLog(admin_id=admin.id,action='verify',entity_type=entity_type,entity_id=entity_id,details={'status':data.status,'evidence':data.evidence,'notes':data.notes})); db.commit(); db.refresh(v)
    return {'status':'ok','verification':serialize(v),'entity':serialize(obj)}

@router.get('/api/verification/{entity_type}/{entity_id}')
def verification_history(entity_type:str,entity_id:int,request:Request,db=Depends(get_db)):
    auth(request,db); return [serialize(x) for x in db.query(Verification).filter(Verification.entity_type==entity_type,Verification.entity_id==entity_id).order_by(Verification.created_at.desc()).all()]
@router.post('/api/verification/evidence')
def add_verification_evidence(data:EvidenceIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    ev=VerificationEvidence(**data.model_dump())
    db.add(ev)
    db.add(AuditLog(admin_id=admin.id, action='verification_evidence_added', entity_type=data.entity_type, entity_id=data.entity_id, details={'evidence_type':data.evidence_type,'source_url':data.source_url}))
    db.commit(); db.refresh(ev)
    return serialize(ev)

@router.get('/api/verification/{entity_type}/{entity_id}/intelligence')
def verification_intelligence(entity_type:str, entity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    result=evidence_score(db, entity_type, entity_id)
    if result['score'] >= 0.80 and result['independent_sources'] >= 2:
        recommendation='Ready for manual verification review'
    elif result['score'] >= 0.55:
        recommendation='Partially supported; collect more independent evidence'
    else:
        recommendation='Insufficient evidence'
    return {**result,'recommendation':recommendation,'status_change_required':True}

@router.post('/api/discovery/candidates/{candidate_id}/deduplicate')
def deduplicate_candidate(candidate_id:int, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    candidate=db.get(DiscoveryCandidate,candidate_id)
    if not candidate: raise HTTPException(404,'کاندید پیدا نشد.')
    matches=find_candidate_duplicates(db,candidate)
    for m in matches:
        update_candidate_trust(db,m)
    update_candidate_trust(db,candidate)
    db.commit()
    return {'candidate_id':candidate.id,'trust_score':candidate.trust_score,'possible_duplicates':[serialize(x) for x in matches]}

@router.post('/api/discovery/candidates/{candidate_id}/merge')
def merge_candidate_duplicates(candidate_id:int, data:CandidateMergeIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    winner=db.get(DiscoveryCandidate,candidate_id)
    if not winner: raise HTTPException(404,'کاندید اصلی پیدا نشد.')
    merged=[]
    for did in data.duplicate_ids:
        dup=db.get(DiscoveryCandidate,did)
        if not dup or dup.id==winner.id: continue
        merge_candidate(db,winner,dup); merged.append(did)
    update_candidate_trust(db,winner)
    db.add(AuditLog(admin_id=admin.id, action='discovery_candidates_merged', entity_type='discovery_candidate', entity_id=winner.id, details={'merged_ids':merged}))
    db.commit(); db.refresh(winner)
    return {'winner':serialize(winner),'merged_ids':merged}



@router.post('/api/discovery/normalize')
def discovery_normalize(data: dict, request: Request, db: Session = Depends(get_db)):
    """Normalize raw commercial evidence without creating trusted entities."""
    auth(request, db)
    from ..discovery.normalization import normalize_commercial_text
    text = str(data.get('text') or '').strip()
    if not text:
        raise HTTPException(400, 'متن برای نرمال‌سازی الزامی است.')
    return normalize_commercial_text(text, source_url=data.get('source_url'), source_title=data.get('source_title'), requested_product=data.get('requested_product'))
