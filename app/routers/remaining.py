from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone
import re
import hashlib
from pathlib import Path
from ..config import get_settings
from ..database import get_db
from ..models import *
from ..schemas import *
from ..security.auth import *
from ..services.rbac import ROLES, permissions_for, require_permission, audit, enforce_mutation_permission
from ..services.multi_market import get_or_create_market, serialize_market, DEFAULT_WEIGHTS, resolve_market
from ..services.trade_rules import serialize_country, serialize_rule, trade_readiness, RULE_TYPES, STATUSES
from ..services.product_compliance import compliance_gate, serialize_profile as serialize_compliance, serialize_requirement, STATUSES as COMPLIANCE_STATUSES, REQ_TYPES
from ..services.import_cost import find_verified_rule, calculate_import_cost, serialize_rule as serialize_import_rule, STATUSES as IMPORT_COST_STATUSES
from ..services.core import *
from ..services.commercial import calculate_offer, deal_decision_engine
from ..services.negotiation import negotiation_engine
from ..services.opportunity_health import calculate_opportunity_health
from ..discovery.engine import discover_from_signal, classify_signal, parse_demand
from ..adapters.google_maps import GoogleMapsAdapter, GoogleMapsError, normalize_places, normalize_route
from ..adapters.divar import DivarAdapter, DivarError, normalize_posts
from ..adapters.firecrawl import FirecrawlAdapter, FirecrawlError, normalize_search
from ..discovery.sources import BUILTIN_SOURCES, build_queries, resolve_sources
from ..discovery.source_discovery import extract_domains, register_discovered
from ..verification.intelligence import canonical_key, source_trust, evidence_score, update_candidate_trust, find_candidate_duplicates, merge_candidate
from ..services.request_guard import auth, serialize
from ..services.freshness import apply_freshness
from ..services.job_queue import create_job, finish_job, heartbeat_job
from ..services.discovery_controls import cached_external, DiscoveryBudgetExceeded
from ..services.fx import resolve_fx_rate, resolve_fx_map
settings=get_settings()
router=APIRouter()
static=Path(__file__).resolve().parent.parent.parent/'static'

@router.get('/',include_in_schema=False)
def index(): return FileResponse(static/'index.html')
@router.get('/api/rbac/me')
def rbac_me(request:Request,db=Depends(get_db)):
 a=auth(request,db); return {'id':a.id,'username':a.username,'role':a.role or 'Viewer','permissions':permissions_for(a.role or 'Viewer')}
@router.get('/api/rbac/roles')
def rbac_roles(request:Request,db=Depends(get_db)):
 require_permission(request,db,'user.manage'); return [{'role':r,'permissions':permissions_for(r)} for r in ROLES]
@router.get('/api/admins')
def admins_list(request:Request,db=Depends(get_db)):
 require_permission(request,db,'user.manage'); return [{'id':a.id,'username':a.username,'role':a.role or 'Viewer','is_active':a.is_active} for a in db.query(Admin).order_by(Admin.username).all()]
@router.post('/api/admins')
def admin_create(data:AdminCreateIn,request:Request,db=Depends(get_db)):
 actor=require_permission(request,db,'user.manage')
 if db.query(Admin).filter(Admin.username==data.username.strip()).first(): raise HTTPException(409,'این نام کاربری قبلاً وجود دارد.')
 a=Admin(username=data.username.strip(),password_hash=hash_password(data.password),role=data.role,is_active=True); db.add(a); db.flush(); audit(db,actor,'admin.created','Admin',a.id,{'role':a.role}); db.commit(); return {'id':a.id,'username':a.username,'role':a.role,'is_active':a.is_active}
@router.patch('/api/admins/{admin_id}/role')
def admin_role(admin_id:int,data:AdminRoleUpdateIn,request:Request,db=Depends(get_db)):
 actor=require_permission(request,db,'user.manage'); a=db.get(Admin,admin_id)
 if not a: raise HTTPException(404,'کاربر پیدا نشد.')
 if a.id==actor.id and data.role!='Super Admin': raise HTTPException(400,'نمی‌توانید نقش مدیریتی نشست خود را کاهش دهید.')
 old=a.role; a.role=data.role; audit(db,actor,'admin.role_changed','Admin',a.id,{'from':old,'to':a.role}); db.commit(); return {'id':a.id,'role':a.role}
@router.patch('/api/admins/{admin_id}/status')
def admin_status(admin_id:int,data:AdminStatusUpdateIn,request:Request,db=Depends(get_db)):
 actor=require_permission(request,db,'user.manage'); a=db.get(Admin,admin_id)
 if not a: raise HTTPException(404,'کاربر پیدا نشد.')
 if a.id==actor.id and not data.is_active: raise HTTPException(400,'نمی‌توانید خودتان را غیرفعال کنید.')
 a.is_active=data.is_active; audit(db,actor,'admin.status_changed','Admin',a.id,{'is_active':a.is_active}); db.commit(); return {'id':a.id,'is_active':a.is_active}
@router.get('/api/audit-logs')
def audit_logs(request:Request,db=Depends(get_db)):
 require_permission(request,db,'audit.read'); return [serialize(x) for x in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()]

@router.get('/api/opportunities')
def opportunities(request:Request,db=Depends(get_db)):
    auth(request,db); return [serialize(x) for x in db.query(Opportunity).filter(Opportunity.is_archived==False).order_by(Opportunity.score.desc()).all()]
@router.get('/api/opportunities/{opportunity_id}/actions')
def opportunity_actions(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    if not db.get(Opportunity, opportunity_id): raise HTTPException(404,'فرصت پیدا نشد.')
    return [serialize(x) for x in db.query(OpportunityAction).filter(OpportunityAction.opportunity_id==opportunity_id).order_by(OpportunityAction.due_at.asc().nullslast(), OpportunityAction.created_at.desc()).all()]

@router.post('/api/opportunities/{opportunity_id}/actions')
def create_opportunity_action(opportunity_id:int, data:OpportunityActionIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    if not db.get(Opportunity, opportunity_id): raise HTTPException(404,'فرصت پیدا نشد.')
    payload=data.model_dump()
    completed_at=datetime.now(timezone.utc) if payload.get('status')=='Completed' else None
    x=OpportunityAction(opportunity_id=opportunity_id, created_by=admin.id, completed_at=completed_at, **payload)
    db.add(x)
    db.add(AuditLog(admin_id=admin.id, action='opportunity_action_created', entity_type='opportunity', entity_id=opportunity_id, details=payload))
    db.commit(); db.refresh(x)
    return serialize(x)

@router.patch('/api/opportunities/{opportunity_id}/actions/{action_id}')
def update_opportunity_action(opportunity_id:int, action_id:int, data:OpportunityActionIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    x=db.get(OpportunityAction, action_id)
    if not x or x.opportunity_id!=opportunity_id: raise HTTPException(404,'اقدام پیدا نشد.')
    for k,v in data.model_dump().items(): setattr(x,k,v)
    x.completed_at=datetime.now(timezone.utc) if x.status=='Completed' else None
    db.add(AuditLog(admin_id=admin.id, action='opportunity_action_updated', entity_type='opportunity_action', entity_id=x.id, details=data.model_dump()))
    db.commit(); db.refresh(x)
    return serialize(x)

@router.get('/api/action-center')
def action_center(request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    now=datetime.now(timezone.utc)
    rows=db.query(OpportunityAction).filter(OpportunityAction.status.in_(['Planned','In Progress'])).order_by(OpportunityAction.due_at.asc().nullslast()).limit(100).all()
    return {'now':now.isoformat(),'items':[serialize(x) for x in rows]}

@router.post('/api/opportunities/rebuild')
def rebuild(request:Request,db=Depends(get_db)):
    auth(request,db); xs=rebuild_opportunities(db); return {'created':len(xs)}
@router.post('/api/search')
def search(data:SearchIn,request:Request,db=Depends(get_db)):
    auth(request,db); p=get_or_create_product(db,data.product); market_name_value=data.market or settings.default_market_name
    if not market_name_value: raise HTTPException(400,'بازار باید به‌صورت مبدأ → مقصد مشخص شود.')
    try: mkt=resolve_market(db,market_name_value)
    except ValueError as exc: raise HTTPException(400,str(exc))
    source,target=mkt.source_country,mkt.target_country; mans=db.query(Manufacturer).filter(Manufacturer.product_id==p.id,Manufacturer.country==source,Manufacturer.is_archived==False).all(); cus=db.query(Customer).filter(Customer.product_id==p.id,Customer.country.ilike(f'%{target}%'),Customer.is_archived==False).all(); ds=db.query(Demand).filter(Demand.product_id==p.id,Demand.country.ilike(f'%{target}%'),Demand.is_archived==False).all(); ops=db.query(Opportunity).filter(Opportunity.product_id==p.id,Opportunity.is_archived==False).all();
    return {'product':serialize(p),'market':serialize_market(mkt),'manufacturers':[serialize(x) for x in mans],'customers':[serialize(x) for x in cus],'demands':[serialize(x) for x in ds],'opportunities':[serialize(x) for x in ops[:data.limit]]}
@router.get('/api/places/search')
async def places(q:str,request:Request,db=Depends(get_db)):
    auth(request,db)
    if not q.strip(): raise HTTPException(400,'عبارت جستجو نمی‌تواند خالی باشد.')
    if not settings.google_maps_api_key: return JSONResponse({'status':'unavailable','message':'Google Maps API Key تنظیم نشده است.'},503)
    try:
        payload=await GoogleMapsAdapter(settings.google_maps_api_key).places_text_search(q.strip())
        return {'status':'ok','query':q,'results':normalize_places(payload)}
    except GoogleMapsError as exc:
        raise HTTPException(502,str(exc)) from exc
@router.post('/api/routes')
async def routes(data:RouteIn,request:Request,db=Depends(get_db)):
    auth(request,db)
    if not settings.google_maps_api_key: return JSONResponse({'status':'unavailable','message':'Google Maps API Key تنظیم نشده است.'},503)
    try:
        payload=await GoogleMapsAdapter(settings.google_maps_api_key).compute_route(data.origin, data.destination)
        return {'status':'ok','origin':data.origin,'destination':data.destination,'route':normalize_route(payload)}
    except GoogleMapsError as exc:
        raise HTTPException(502,str(exc)) from exc

@router.get('/api/discovery/sources')
def discovery_sources(request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    return {'sources':[{'key':x.key,'label':x.label,'channel':x.channel,'domains':list(x.domains),'description':x.description,'configured': bool(settings.google_maps_api_key) if x.channel=='google_places' else bool(settings.divar_api_key or settings.firecrawl_api_key) if x.channel=='divar' else bool(settings.firecrawl_api_key) if x.channel=='firecrawl' else False} for x in BUILTIN_SOURCES]}

@router.post('/api/discovery/external')
async def external_discovery(data:ExternalDiscoveryIn, request:Request, db=Depends(get_db)):
    return await _run_external_discovery(data, request, db, None)

async def _run_external_discovery(data:ExternalDiscoveryIn, request:Request|None, db:Session, existing_job=None, worker_admin=None):
    admin=worker_admin or auth(request,db)
    product=data.product.strip()
    market_name_value=(data.market or settings.default_market_name or '').strip()
    if not market_name_value: raise HTTPException(400,'بازار باید به‌صورت مبدأ → مقصد مشخص شود.')
    try:
        market_obj=resolve_market(db,market_name_value,allow_create=False)
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    if not market_obj: raise HTTPException(400,'بازار انتخاب‌شده وجود ندارد.')
    target=market_obj.target_country
    if not product or not target: raise HTTPException(400,'محصول و بازار هدف الزامی هستند.')
    sources=resolve_sources(data.sources,data.domains)
    if not sources: raise HTTPException(400,'حداقل یک منبع معتبر انتخاب کنید.')
    collected=[]; errors=[]; source_stats=[]; seen_urls=set(); seen_candidates=set(); discovered_sources=[]; budget=min(data.max_results,settings.discovery_max_results,50)
    job=existing_job or create_job(db,'external_discovery',data.model_dump(),max_requests=min(settings.discovery_request_budget,50),max_retries=settings.discovery_max_retries,created_by=admin.id)
    if job.status != 'running':
        from uuid import uuid4
        job.status='running'; job.started_at=datetime.now(timezone.utc); job.heartbeat_at=job.started_at; job.lease_token=uuid4().hex
    db.flush(); db.commit(); db.refresh(job)
    async def external_call(source_key, query, params, fetcher):
        try:
            if not heartbeat_job(db, job):
                raise RuntimeError('Discovery job lease was lost before external request.')
            db.commit()
            value=await cached_external(db,job,source_key=source_key,query=query,params=params,user_id=admin.id,settings=settings,fetcher=fetcher)
            if not heartbeat_job(db, job):
                raise RuntimeError('Discovery job lease was lost during external request.')
            db.commit()
            return value
        except DiscoveryBudgetExceeded as exc:
            finish_job(db,job,'failed',error=str(exc)); db.commit()
            raise HTTPException(429,str(exc))

    for source in sources:
        source_results=0; queries=build_queries(product,target,data.query_terms,source)
        for query in queries:
            if source.channel=='google_places':
                if not settings.google_maps_api_key:
                    errors.append(f'{source.label}: Google Maps API Key تنظیم نشده است.'); continue
                try:
                    payload,_meta=await external_call(source.key, f'{product} manufacturers buyers in {target}', {'operation':'places_text_search','max_result_count':min(budget,20)}, lambda: GoogleMapsAdapter(settings.google_maps_api_key,settings.discovery_timeout_seconds).places_text_search(f'{product} manufacturers buyers in {target}',max_result_count=min(budget,20)))
                    for place in normalize_places(payload):
                        raw=' | '.join(filter(None,[place.get('name'),place.get('address'),' '.join(place.get('types') or []),product,target]))
                        h=hashlib.sha256((raw.lower()+'|'+(place.get('place_id') or '')).encode()).hexdigest()
                        sig=db.query(SourceSignal).filter(SourceSignal.content_hash==h).first()
                        if not sig:
                            sig=SourceSignal(raw_text=raw,source_title='Google Places',source_url=place.get('maps_url'),external_key=place.get('place_id'),content_hash=h,verification_status='Unverified',confidence=0.55,normalized_payload={'channel':'google_places','market':target,'source_key':source.key}); db.add(sig); db.flush()
                        ext=classify_signal(raw,source_name='Google Places',requested_product=product,place=place)
                        ckey=canonical_key(ext.company_name,ext.country or target,ext.city)
                        if ckey and ckey in seen_candidates:
                            continue
                        if ckey:
                            seen_candidates.add(ckey)
                        cand=DiscoveryCandidate(source_signal_id=sig.id,name=ext.company_name,country=ext.country or target,city=ext.city,activity_type=ext.activity_type,product_name=ext.product_name,candidate_type=ext.customer_type,demand_likelihood=ext.demand_likelihood,confidence=ext.confidence,evidence={**ext.evidence,'place_id':place.get('place_id'),'source_key':source.key},source_url=place.get('maps_url'),source_title='Google Places',status='Review',canonical_key=ckey,trust_score=ext.confidence)
                        db.add(cand); db.flush(); collected.append({'channel':'google_places','source_key':source.key,'candidate':serialize(cand),'place':place,'extraction':ext.evidence}); source_results+=1
                        if len(collected)>=budget: break
                except GoogleMapsError as exc: errors.append(f'{source.label}: {exc}')
                break
            if source.channel=='divar':
                # Prefer the official Divar Open Platform API when configured.
                # Without a key, fall back to permitted public web discovery.
                if settings.divar_api_key:
                    try:
                        payload,_meta=await external_call(source.key, query, {'operation':'divar_search','limit':min(budget,50)}, lambda: DivarAdapter(settings.divar_api_key,settings.discovery_timeout_seconds).search(query,limit=min(budget,50)))
                        for item in normalize_posts(payload):
                            url=item.get('url'); text='\n'.join(filter(None,[item.get('title'),item.get('description')]))[:30000]
                            if url and url in seen_urls: continue
                            if not text.strip(): continue
                            if url: seen_urls.add(url)
                            ext=classify_signal(text,source_name='دیوار',requested_product=product); demand=parse_demand(text,product)
                            key=item.get('id') or url or hashlib.sha256(text.encode()).hexdigest(); h=hashlib.sha256((text.lower()+'|'+key).encode()).hexdigest()
                            sig=db.query(SourceSignal).filter(SourceSignal.content_hash==h).first()
                            if not sig:
                                sig=SourceSignal(raw_text=text,source_title=item.get('title') or 'دیوار',source_url=url,external_key=key,content_hash=h,verification_status='Unverified',confidence=ext.confidence,normalized_payload={'channel':'divar','market':target,'source_key':source.key,'query':query,'demand':demand}); db.add(sig); db.flush()
                            ckey=canonical_key(ext.company_name,ext.country or target,ext.city)
                            if ckey and ckey in seen_candidates: continue
                            if ckey: seen_candidates.add(ckey)
                            cand=DiscoveryCandidate(source_signal_id=sig.id,name=ext.company_name or item.get('title'),country=ext.country or target,city=ext.city,activity_type=ext.activity_type,product_name=ext.product_name or product,candidate_type=('Active Purchase Demand' if demand['is_demand_signal'] else ext.customer_type),demand_likelihood=max(ext.demand_likelihood,demand['confidence'] if demand['is_demand_signal'] else 0),confidence=ext.confidence,evidence={**ext.evidence,'demand':demand,'source_key':source.key,'query':query,'divar_post_id':item.get('id')},source_url=url,source_title=item.get('title') or 'دیوار',status='Review',canonical_key=ckey,trust_score=ext.confidence)
                            db.add(cand); db.flush(); collected.append({'channel':'divar','source_key':source.key,'candidate':serialize(cand),'source':item,'demand':demand,'query':query}); source_results+=1
                            if len(collected)>=budget: break
                    except DivarError as exc: errors.append(f'{source.label}: {exc}')
                else:
                    try:
                        fallback_query = query + " " + " ".join(f"site:{d}" for d in source.domains)
                        fallback,_meta=await external_call(source.key, fallback_query, {'operation':'firecrawl_search','limit':min(budget,50),'scrape_markdown':True}, lambda: FirecrawlAdapter(settings.firecrawl_api_key,settings.discovery_timeout_seconds).search(fallback_query,limit=min(budget,50),scrape_markdown=True)) if settings.firecrawl_api_key else (None,{})
                        if fallback is None:
                            errors.append(f'{source.label}: API Key دیوار و Firecrawl تنظیم نشده است.')
                        else:
                            items=normalize_search(fallback)
                            for item in items:
                                url=item.get('url')
                                if url and url in seen_urls: continue
                                text='\n'.join(filter(None,[item.get('title'),item.get('description'),item.get('markdown')]))[:30000]
                                if not text.strip(): continue
                                if url: seen_urls.add(url)
                                ext=classify_signal(text,source_name='دیوار',requested_product=product); demand=parse_demand(text,product)
                                key=url or hashlib.sha256(text.encode()).hexdigest(); h=hashlib.sha256((text.lower()+'|'+key).encode()).hexdigest()
                                sig=db.query(SourceSignal).filter(SourceSignal.content_hash==h).first()
                                if not sig:
                                    sig=SourceSignal(raw_text=text,source_title=item.get('title') or 'دیوار',source_url=url,external_key=key,content_hash=h,verification_status='Unverified',confidence=ext.confidence,normalized_payload={'channel':'divar_public_web','market':target,'source_key':source.key,'query':query,'demand':demand}); db.add(sig); db.flush()
                                ckey=canonical_key(ext.company_name,ext.country or target,ext.city)
                                if ckey and ckey in seen_candidates: continue
                                if ckey: seen_candidates.add(ckey)
                                cand=DiscoveryCandidate(source_signal_id=sig.id,name=ext.company_name,country=ext.country or target,city=ext.city,activity_type=ext.activity_type,product_name=ext.product_name or product,candidate_type=('Active Purchase Demand' if demand['is_demand_signal'] else ext.customer_type),demand_likelihood=max(ext.demand_likelihood,demand['confidence'] if demand['is_demand_signal'] else 0),confidence=ext.confidence,evidence={**ext.evidence,'demand':demand,'source_key':source.key,'query':query},source_url=url,source_title=item.get('title') or 'دیوار',status='Review',canonical_key=ckey,trust_score=ext.confidence)
                                db.add(cand); db.flush(); collected.append({'channel':'divar_public_web','source_key':source.key,'candidate':serialize(cand),'source':item,'demand':demand,'query':query}); source_results+=1
                                if len(collected)>=budget: break
                    except FirecrawlError as exc: errors.append(f'{source.label}: {exc}')
                if len(collected)>=budget: break
            if source.channel=='firecrawl':
                if not settings.firecrawl_api_key:
                    errors.append(f'{source.label}: Firecrawl API Key تنظیم نشده است.'); break
                try:
                    payload,_meta=await external_call(source.key, query, {'operation':'firecrawl_search','limit':min(budget,50),'scrape_markdown':True,'domains':list(source.domains)}, lambda: FirecrawlAdapter(settings.firecrawl_api_key,settings.discovery_timeout_seconds).search(query,limit=min(budget,50),scrape_markdown=True))
                    for item in normalize_search(payload):
                        url=item.get('url')
                        if url and url in seen_urls: continue
                        text='\n'.join(filter(None,[item.get('title'),item.get('description'),item.get('markdown')]))[:30000]
                        if not text.strip(): continue
                        if url: seen_urls.add(url)
                        ext=classify_signal(text,source_name=source.label,requested_product=product); demand=parse_demand(text,product); quality={**ext.evidence, 'source_url':url, 'requested_product':product}; key=url or hashlib.sha256(text.encode()).hexdigest(); h=hashlib.sha256((text.lower()+'|'+key).encode()).hexdigest()
                        sig=db.query(SourceSignal).filter(SourceSignal.content_hash==h).first()
                        if not sig:
                            sig=SourceSignal(raw_text=text,source_title=item.get('title') or source.label,source_url=url,external_key=key,content_hash=h,verification_status='Unverified',confidence=ext.confidence,normalized_payload={'channel':'firecrawl','market':target,'demand':demand,'query':query,'domains':list(source.domains),'source_key':source.key},observed_at=datetime.now(timezone.utc)); apply_freshness(sig, observed_at=sig.observed_at, published_at=item.get('published_at'), policy='purchase_demand'); db.add(sig); db.flush()
                        if demand['is_demand_signal'] and demand.get('product') and demand.get('country'):
                            prod=get_or_create_product(db,demand['product']); existing_d=db.query(Demand).filter(Demand.source_url==url,Demand.product_id==prod.id).first() if url else None
                            if not existing_d: db.add(Demand(product_id=prod.id,raw_text=text[:5000],quantity=demand.get('quantity'),unit=demand.get('unit'),country=demand.get('country'),city=demand.get('city'),urgency=demand.get('urgency'),source_url=url,published_at=None,confidence=demand.get('confidence',0),verification_status='Unverified'))
                        ckey=canonical_key(ext.company_name,ext.country or target,ext.city)
                        if ckey and ckey in seen_candidates:
                            continue
                        if ckey:
                            seen_candidates.add(ckey)
                        cand=DiscoveryCandidate(source_signal_id=sig.id,name=ext.company_name,country=ext.country or target,city=ext.city,activity_type=ext.activity_type,product_name=ext.product_name or product,candidate_type=('Active Purchase Demand' if demand['is_demand_signal'] else ext.customer_type),demand_likelihood=max(ext.demand_likelihood,demand['confidence'] if demand['is_demand_signal'] else 0),confidence=ext.confidence,evidence={**quality,'demand':demand,'source_key':source.key,'query':query},source_url=url,source_title=item.get('title') or source.label,status='Review',canonical_key=ckey,trust_score=ext.confidence)
                        db.add(cand); db.flush(); collected.append({'channel':'firecrawl','source_key':source.key,'candidate':serialize(cand),'source':item,'demand':demand,'extraction':quality,'query':query}); source_results+=1
                        if len(collected)>=budget: break
                except FirecrawlError as exc: errors.append(f'{source.label}: {exc}')
            if len(collected)>=budget: break
        source_stats.append({'source_key':source.key,'label':source.label,'channel':source.channel,'domains':list(source.domains),'queries':queries,'results':source_results,'configured':bool(settings.google_maps_api_key) if source.channel=='google_places' else bool(settings.divar_api_key or settings.firecrawl_api_key) if source.channel=='divar' else bool(settings.firecrawl_api_key) if source.channel=='firecrawl' else False})
        if len(collected)>=budget: break
    # Bounded source discovery: inspect public result URLs, register new domains,
    # and perform at most one additional public-web query per discovered domain.
    candidate_items = [x.get('source') for x in collected if isinstance(x, dict) and isinstance(x.get('source'), dict)]
    domains_found = extract_domains(candidate_items, excluded={d for src in sources for d in src.domains})
    discovered_sources = register_discovered(db, domains_found[:10], product=product, market=target)
    if discovered_sources and settings.firecrawl_api_key and len(collected) < budget:
        for ds in discovered_sources[:5]:
            if len(collected) >= budget: break
            domain = ds['domain']
            query = f'{product} {target} buyer supplier site:{domain}'
            try:
                payload,_meta = await external_call(f'site:{domain}', query, {'operation':'firecrawl_search','limit':min(5,budget-len(collected)),'scrape_markdown':True}, lambda: FirecrawlAdapter(settings.firecrawl_api_key, settings.discovery_timeout_seconds).search(query, limit=min(5, budget-len(collected)), scrape_markdown=True))
                for item in normalize_search(payload):
                    url=item.get('url')
                    if not url or url in seen_urls: continue
                    text='\n'.join(filter(None,[item.get('title'),item.get('description'),item.get('markdown')]))[:30000]
                    if not text.strip(): continue
                    seen_urls.add(url)
                    ext=classify_signal(text,source_name=domain,requested_product=product); demand=parse_demand(text,product)
                    key=url; h=hashlib.sha256((text.lower()+'|'+key).encode()).hexdigest()
                    sig=db.query(SourceSignal).filter(SourceSignal.content_hash==h).first()
                    if not sig:
                        sig=SourceSignal(raw_text=text,source_title=item.get('title') or domain,source_url=url,external_key=key,content_hash=h,verification_status='Unverified',confidence=ext.confidence,normalized_payload={'channel':'discovered_public_web','domain':domain,'market':target,'query':query,'demand':demand,'discovery_score':ds['score']},observed_at=datetime.now(timezone.utc)); apply_freshness(sig, observed_at=sig.observed_at, published_at=item.get('published_at'), policy='purchase_demand'); db.add(sig); db.flush()
                    collected.append({'channel':'discovered_public_web','source_key':f'site:{domain}','candidate':None,'source':item,'demand':demand,'extraction':ext.evidence,'query':query,'discovery':ds});
                    if len(collected)>=budget: break
            except FirecrawlError as exc:
                errors.append(f'{domain}: {exc}')
    try:
        finish_job(db,job,'completed',{'count':len(collected),'errors':errors,'discovered_sources':discovered_sources})
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(500,'ذخیره نتایج کشف خارجی با خطا مواجه شد.')
    return {'status':'ok','query':f'{product} {target}','market':serialize_market(market_obj),'count':len(collected),'results':collected,'errors':errors,'sources':source_stats,'discovered_sources':discovered_sources,'discovery_depth':1,'discovery_budget':{'max_domains':10,'max_expansion_sources':5},'job_id':job.id,'requests_used':job.requests_used,'cache_enabled':True}

@router.post('/api/discovery/ingest')
def ingest_signals(items:list[SignalIngestItem], request:Request, db=Depends(get_db)):
    auth(request,db); created=0; deduped=0
    for item in items[:100]:
        h=hashlib.sha256((item.raw_text.strip().lower()+'|'+(item.source_url or '')+'|'+(item.external_key or '')).encode()).hexdigest()
        if db.query(SourceSignal).filter(SourceSignal.content_hash==h).first():
            deduped += 1; continue
        demand=parse_demand(item.raw_text)
        sig=SourceSignal(source_id=item.source_id,raw_text=item.raw_text.strip(),source_url=item.source_url,source_title=item.source_title,published_at=item.published_at,external_key=item.external_key,content_hash=h,verification_status='Unverified',confidence=demand['confidence'],normalized_payload={'demand':demand},observed_at=datetime.now(timezone.utc))
        apply_freshness(sig, observed_at=sig.observed_at, published_at=sig.published_at, policy='purchase_demand')
        db.add(sig); created += 1
    db.commit(); return {'created':created,'deduplicated':deduped}

@router.get('/api/discovery/status')
def discovery_status(request:Request, db=Depends(get_db)):
    auth(request,db)
    return {'firecrawl_configured':bool(settings.firecrawl_api_key),'google_maps_configured':bool(settings.google_maps_api_key),'candidates_review':db.query(DiscoveryCandidate).filter(DiscoveryCandidate.status=='Review',DiscoveryCandidate.is_archived==False).count(),'unverified_signals':db.query(SourceSignal).filter(SourceSignal.verification_status=='Unverified').count(),'low_trust_candidates':db.query(DiscoveryCandidate).filter(DiscoveryCandidate.trust_score < 0.55, DiscoveryCandidate.is_archived==False).count(),'verified_evidence_items':db.query(VerificationEvidence).count()}
@router.get('/api/status')
def status(request:Request,db=Depends(get_db)):
    auth(request,db); return {'version':settings.version,'google_maps_configured':bool(settings.google_maps_api_key),'environment':settings.environment}

# V20.9 RFQ & Communication Center

def _opportunity_context(db, opportunity_id:int):
    op=db.get(Opportunity, opportunity_id)
    if not op: raise HTTPException(404,'فرصت پیدا نشد.')
    manufacturer=db.get(Manufacturer, op.manufacturer_id)
    customer=db.get(Customer, op.customer_id)
    product=db.get(Product, op.product_id)
    demand=db.get(Demand, op.demand_id) if op.demand_id else None
    return op, manufacturer, customer, product, demand

def _rfq_text(channel, language, op, manufacturer, customer, product, demand, tone):
    product_name=product.name if product else 'the requested product'
    qty=f"{demand.quantity:g} {demand.unit}" if demand and demand.quantity is not None and demand.unit else 'your required quantity'
    city=(customer.city if customer else None) or (demand.city if demand else None) or (customer.country if customer else 'the destination market')
    specs=(product.specifications or {}) if product else {}
    spec_text='; '.join(f'{k}: {v}' for k,v in specs.items())
    if language=='fa':
        if channel=='whatsapp':
            return f"سلام،\nما از طرف {manufacturer.name if manufacturer else 'تأمین‌کننده ایرانی'} در زمینه تأمین {product_name} برای بازار {customer.country if customer else 'هدف'} فعالیت می‌کنیم.\nبا توجه به نیاز ثبت‌شده، لطفاً مقدار موردنیاز ({qty})، مشخصات فنی، بسته‌بندی و زمان تحویل موردنظر خود را تأیید فرمایید.\nدر صورت تأیید، مشخصات فنی و قیمت FOB/CIF را ارسال می‌کنیم.\nبا احترام"
        return f"درخواست تأمین {product_name} — {city}\n\nسلام،\nبرای بررسی همکاری تجاری، لطفاً مقدار موردنیاز ({qty})، مشخصات فنی، بسته‌بندی، مقصد نهایی و زمان تحویل موردنظر را اعلام فرمایید.\nما امکان ارائه پیشنهاد FOB/CIF و مشخصات فنی را داریم.\nبا احترام"
    if language=='ps':
        return f"سلام،\nموږ د {product_name} د برابرولو لپاره د ایران له عرضه کوونکي سره کار کوو. د ثبت شوې اړتیا له مخې مهرباني وکړئ د اړتیا مقدار ({qty})، تخنیکي مشخصات، بسته بندي او د تحویل وخت تایید کړئ.\nله تایید وروسته به د FOB/CIF بیه او تخنیکي مشخصات درولېږو.\nپه درنښت"
    # English
    if channel=='whatsapp' or tone=='concise':
        return f"Hello,\nWe represent an Iranian supplier of {product_name}. We are contacting you regarding the identified requirement in {city}. Please confirm the required quantity ({qty}), technical specifications, packaging and delivery schedule. We can then provide technical documents and FOB/CIF pricing.\nBest regards"
    return f"Subject: Supply Inquiry — {product_name}\n\nDear {customer.name if customer else 'Procurement Team'},\n\nWe are contacting you regarding a potential supply opportunity for {product_name} to {city}.\n\nCould you please confirm:\n1. Required quantity: {qty}\n2. Technical specifications: {spec_text or 'Please advise'}\n3. Packaging requirements\n4. Destination and preferred Incoterm (FOB/CIF)\n5. Required delivery schedule\n\nUpon confirmation, we can provide the relevant technical specification, commercial offer and FOB/CIF quotation.\n\nBest regards"

def _rfq_title(channel, product, customer):
    prefix={'whatsapp':'WhatsApp Inquiry','email':'Supply Inquiry','rfq':'RFQ'}[channel]
    return f"{prefix} — {product.name if product else 'Product'} — {customer.name if customer else 'Customer'}"

@router.post('/api/opportunities/{opportunity_id}/rfq/generate')
def generate_rfq(opportunity_id:int, data:RFQGenerateIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    op, manufacturer, customer, product, demand=_opportunity_context(db,opportunity_id)
    body=_rfq_text(data.channel,data.language,op,manufacturer,customer,product,demand,data.tone)
    title=_rfq_title(data.channel,product,customer)
    doc=RFQDocument(opportunity_id=opportunity_id,channel=data.channel,language=data.language,title=title,body=body,status='Draft',metadata_json={'tone':data.tone,'generated_from':{'product_id':product.id if product else None,'customer_id':customer.id if customer else None,'demand_id':demand.id if demand else None}},created_by=admin.id)
    db.add(doc); db.add(AuditLog(admin_id=admin.id,action='rfq_generated',entity_type='opportunity',entity_id=opportunity_id,details={'rfq_channel':data.channel,'language':data.language}))
    db.commit(); db.refresh(doc)
    return serialize(doc)

@router.get('/api/opportunities/{opportunity_id}/rfqs')
def list_rfqs(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db); _opportunity_context(db,opportunity_id)
    return [serialize(x) for x in db.query(RFQDocument).filter(RFQDocument.opportunity_id==opportunity_id).order_by(RFQDocument.created_at.desc()).all()]

@router.patch('/api/opportunities/{opportunity_id}/rfqs/{rfq_id}')
def update_rfq(opportunity_id:int, rfq_id:int, data:RFQUpdateIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _opportunity_context(db,opportunity_id)
    doc=db.get(RFQDocument,rfq_id)
    if not doc or doc.opportunity_id!=opportunity_id: raise HTTPException(404,'RFQ پیدا نشد.')
    doc.status=data.status
    doc.response_due_at=data.response_due_at
    if data.status=='Sent' and not doc.sent_at: doc.sent_at=datetime.now(timezone.utc)
    db.add(AuditLog(admin_id=admin.id,action='rfq_updated',entity_type='rfq',entity_id=rfq_id,details=data.model_dump()))
    db.commit(); db.refresh(doc); return serialize(doc)

@router.get('/api/opportunities/{opportunity_id}/communications')
def list_communications(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db); _opportunity_context(db,opportunity_id)
    return [serialize(x) for x in db.query(CommunicationLog).filter(CommunicationLog.opportunity_id==opportunity_id).order_by(CommunicationLog.created_at.desc()).all()]

@router.post('/api/opportunities/{opportunity_id}/communications')
def create_communication(opportunity_id:int, data:CommunicationIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _opportunity_context(db,opportunity_id)
    sent_at=data.sent_at or (datetime.now(timezone.utc) if data.status=='Sent' else None)
    log=CommunicationLog(opportunity_id=opportunity_id,channel=data.channel,direction=data.direction,status=data.status,recipient=data.recipient,subject=data.subject,message=data.message,sent_at=sent_at,response_summary=data.response_summary,created_by=admin.id)
    db.add(log)
    if data.status=='Sent':
        db.add(OpportunityAction(opportunity_id=opportunity_id,created_by=admin.id,action_type='follow_up',status='Completed',subject=data.subject or f'{data.channel} communication',notes=data.message[:1000],channel=data.channel,completed_at=sent_at,result='Communication logged as sent'))
    db.add(AuditLog(admin_id=admin.id,action='communication_logged',entity_type='opportunity',entity_id=opportunity_id,details={'channel':data.channel,'direction':data.direction,'status':data.status}))
    db.commit(); db.refresh(log); return serialize(log)

@router.get('/api/rfq-center')
def rfq_center(request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    docs=db.query(RFQDocument).order_by(RFQDocument.created_at.desc()).limit(100).all()
    return {'items':[serialize(x) for x in docs],'counts':{s:db.query(RFQDocument).filter(RFQDocument.status==s).count() for s in ['Draft','Approved','Sent','Responded','Closed','Cancelled']}}

# V21.0 Commercial Intelligence
from ..services.commercial import calculate_offer, compare_quotes

def _commercial_context(db, opportunity_id:int):
    op=db.get(Opportunity, opportunity_id)
    if not op: raise HTTPException(404,'فرصت پیدا نشد.')
    return op

@router.get('/api/opportunities/{opportunity_id}/supplier-quotes')
def supplier_quotes(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db); _commercial_context(db,opportunity_id)
    rows=db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==opportunity_id).order_by(SupplierQuote.created_at.desc()).all()
    return {'items':[serialize(x) for x in rows], 'comparison':compare_quotes(rows)}

@router.post('/api/opportunities/{opportunity_id}/supplier-quotes')
def create_supplier_quote(opportunity_id:int, data:SupplierQuoteIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _commercial_context(db,opportunity_id)
    payload=data.model_dump(); q=SupplierQuote(opportunity_id=opportunity_id, **payload)
    db.add(q); db.add(AuditLog(admin_id=admin.id,action='supplier_quote_created',entity_type='opportunity',entity_id=opportunity_id,details=payload))
    db.commit(); db.refresh(q)
    return serialize(q)

@router.patch('/api/opportunities/{opportunity_id}/supplier-quotes/{quote_id}')
def update_supplier_quote(opportunity_id:int, quote_id:int, data:SupplierQuoteIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _commercial_context(db,opportunity_id)
    q=db.get(SupplierQuote,quote_id)
    if not q or q.opportunity_id!=opportunity_id: raise HTTPException(404,'پیشنهاد تأمین‌کننده پیدا نشد.')
    for k,v in data.model_dump().items(): setattr(q,k,v)
    db.add(AuditLog(admin_id=admin.id,action='supplier_quote_updated',entity_type='supplier_quote',entity_id=q.id,details=data.model_dump()))
    db.commit(); db.refresh(q); return serialize(q)

@router.get('/api/opportunities/{opportunity_id}/commercial-offers')
def commercial_offers(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db); _commercial_context(db,opportunity_id)
    return [serialize(x) for x in db.query(CommercialOffer).filter(CommercialOffer.opportunity_id==opportunity_id).order_by(CommercialOffer.created_at.desc()).all()]

def _derive_offer_fx(data, db):
    payload = data.model_dump()
    quote = db.get(SupplierQuote, data.supplier_quote_id) if getattr(data, 'supplier_quote_id', None) else None
    source_currency = quote.currency if quote else data.currency
    target_currency = data.currency
    rate, fx_row = resolve_fx_rate(db, source_currency, target_currency)
    payload['exchange_rate'] = rate
    payload['fx_rate_id'] = fx_row.id if fx_row else None
    if fx_row is not None:
        assumptions = dict(payload.get('assumptions') or {})
        assumptions['fx_provenance'] = {'fx_rate_id': fx_row.id, 'source_id': fx_row.source_id, 'source_url': fx_row.source_url, 'observed_at': fx_row.observed_at.isoformat() if fx_row.observed_at else None, 'confidence': fx_row.confidence}
        payload['assumptions'] = assumptions
    return data.model_copy(update=payload), fx_row

def _build_offer(data, db=None):
    # First calculate the commercial FOB selling price; when a logistics scenario is
    # selected, freight/insurance/customs are applied exactly once by the logistics engine.
    if db is not None and getattr(data, 'logistics_scenario_id', None):
        scenario=db.get(LogisticsScenario, data.logistics_scenario_id)
        if not scenario: raise HTTPException(404,'سناریوی حمل پیدا نشد.')
        base_data=data.model_copy(update={'freight_cost':0,'insurance_cost':0,'customs_cost':0,'other_cost':0})
        result=calculate_offer(base_data)
        landed=scenario_summary(scenario, result['fob_total'], data.quantity)
        result.update({'cfr_total':landed['cfr_total'],'cfr_unit_price':landed['cfr_unit_price'],'cif_total':landed['cif_total'],'cif_unit_price':landed['cif_unit_price'],'landed_total':landed['landed_total'],'landed_unit_price':landed['landed_unit_price'],'freight_cost':landed['freight_total'],'insurance_cost':landed['insurance_total'],'customs_cost':landed['customs_total'],'other_cost':landed['other_cost']})
        return result
    return calculate_offer(data)

@router.post('/api/opportunities/{opportunity_id}/commercial-offers/calculate')
def calculate_commercial_offer(opportunity_id:int, data:CommercialOfferIn, request:Request, db:Session=Depends(get_db)):
    auth(request,db); _commercial_context(db,opportunity_id)
    data, fx_row = _derive_offer_fx(data, db)
    result=_build_offer(data, db)
    return {'status':'calculated','currency':data.currency,'exchange_rate':data.exchange_rate,'fx_rate_id':fx_row.id if fx_row else None,'calculation':result,'fx_provenance':serialize(fx_row) if fx_row else None}

@router.post('/api/opportunities/{opportunity_id}/commercial-offers')
def create_commercial_offer(opportunity_id:int, data:CommercialOfferIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _commercial_context(db,opportunity_id)
    data, fx_row = _derive_offer_fx(data, db)
    result=_build_offer(data, db)
    payload=data.model_dump(); payload.update(result)
    # calculation-only helper fields are intentionally kept out of the DB model
    payload.pop('commission_amount',None); payload.pop('base_cost',None); payload.pop('fob_cost_before_margin',None)
    offer=CommercialOffer(opportunity_id=opportunity_id,created_by=admin.id,**payload)
    db.add(offer); db.add(AuditLog(admin_id=admin.id,action='commercial_offer_created',entity_type='opportunity',entity_id=opportunity_id,details={'offer_status':data.status,'currency':data.currency}))
    db.commit(); db.refresh(offer)
    return {'offer':serialize(offer),'calculation':result}

@router.patch('/api/opportunities/{opportunity_id}/commercial-offers/{offer_id}')
def update_commercial_offer(opportunity_id:int, offer_id:int, data:CommercialOfferUpdateIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _commercial_context(db,opportunity_id)
    offer=db.get(CommercialOffer,offer_id)
    if not offer or offer.opportunity_id!=opportunity_id: raise HTTPException(404,'پیشنهاد تجاری پیدا نشد.')
    data, fx_row = _derive_offer_fx(data, db)
    result=_build_offer(data, db); payload=data.model_dump(); payload.update(result)
    for k,v in payload.items():
        if hasattr(offer,k): setattr(offer,k,v)
    db.add(AuditLog(admin_id=admin.id,action='commercial_offer_updated',entity_type='commercial_offer',entity_id=offer.id,details={'status':data.status}))
    db.commit(); db.refresh(offer); return {'offer':serialize(offer),'calculation':result}

@router.get('/api/commercial-intelligence')
def commercial_intelligence(request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    offers=db.query(CommercialOffer).filter(CommercialOffer.status.notin_(['Closed','Cancelled'])).order_by(CommercialOffer.created_at.desc()).limit(100).all()
    quotes=db.query(SupplierQuote).order_by(SupplierQuote.created_at.desc()).limit(100).all()
    return {'offers':[serialize(x) for x in offers], 'supplier_quotes':compare_quotes(quotes), 'currencies':sorted({x.currency for x in quotes})}

# V21.1 Logistics Intelligence
from ..services.logistics import calculate_logistics, scenario_summary

def _logistics_context(db, opportunity_id:int):
    op=db.get(Opportunity, opportunity_id)
    if not op: raise HTTPException(404,'فرصت پیدا نشد.')
    return op

@router.get('/api/opportunities/{opportunity_id}/logistics-scenarios')
def logistics_scenarios(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db); _logistics_context(db,opportunity_id)
    rows=db.query(LogisticsScenario).filter(LogisticsScenario.opportunity_id==opportunity_id, LogisticsScenario.is_active==True).order_by(LogisticsScenario.created_at.desc()).all()
    return [serialize(x) for x in rows]

@router.post('/api/opportunities/{opportunity_id}/logistics-scenarios')
def create_logistics_scenario(opportunity_id:int, data:LogisticsScenarioIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _logistics_context(db,opportunity_id)
    row=LogisticsScenario(opportunity_id=opportunity_id, **data.model_dump())
    db.add(row); db.add(AuditLog(admin_id=admin.id, action='logistics_scenario_created', entity_type='opportunity', entity_id=opportunity_id, details={'name':data.name,'mode':data.transport_mode,'origin':data.origin,'destination':data.destination}))
    db.commit(); db.refresh(row)
    return serialize(row)

@router.patch('/api/opportunities/{opportunity_id}/logistics-scenarios/{scenario_id}')
def update_logistics_scenario(opportunity_id:int, scenario_id:int, data:LogisticsScenarioIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _logistics_context(db,opportunity_id)
    row=db.get(LogisticsScenario,scenario_id)
    if not row or row.opportunity_id!=opportunity_id: raise HTTPException(404,'سناریوی حمل پیدا نشد.')
    for k,v in data.model_dump().items(): setattr(row,k,v)
    db.add(AuditLog(admin_id=admin.id, action='logistics_scenario_updated', entity_type='logistics_scenario', entity_id=row.id, details={'name':row.name}))
    db.commit(); db.refresh(row); return serialize(row)

@router.post('/api/opportunities/{opportunity_id}/logistics/calculate')
def calculate_logistics_for_opportunity(opportunity_id:int, data:LogisticsCalculateIn, request:Request, db:Session=Depends(get_db)):
    auth(request,db); _logistics_context(db,opportunity_id)
    return {'status':'calculated','calculation':calculate_logistics(**data.model_dump())}

@router.post('/api/opportunities/{opportunity_id}/logistics/from-route')
async def create_logistics_from_route(opportunity_id:int, data:RouteIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _logistics_context(db,opportunity_id)
    if not settings.google_maps_api_key:
        return JSONResponse({'status':'unavailable','message':'Google Maps API Key تنظیم نشده است.'},503)
    try:
        payload=await GoogleMapsAdapter(settings.google_maps_api_key).compute_route(data.origin,data.destination)
        route=normalize_route(payload)
    except GoogleMapsError as exc:
        raise HTTPException(502,str(exc)) from exc
    if not route.get('found'): raise HTTPException(404,'مسیر قابل محاسبه پیدا نشد.')
    row=LogisticsScenario(opportunity_id=opportunity_id,name=f"Google Route — {data.origin} → {data.destination}",origin=data.origin,destination=data.destination,transport_mode='road',distance_km=route.get('distance_km'),transit_days=(route.get('duration_seconds') or 0)/86400,assumptions={'route_source':'Google Routes','route':route},verification_status='Partially Verified')
    db.add(row); db.add(AuditLog(admin_id=admin.id,action='logistics_route_imported',entity_type='logistics_scenario',entity_id=0,details={'origin':data.origin,'destination':data.destination,'route':route}))
    db.commit(); db.refresh(row)
    return {'scenario':serialize(row),'route':route}

# V21.2 Supplier & Route Comparison Engine
from ..services.comparison import compare_supplier_routes

@router.post('/api/opportunities/{opportunity_id}/commercial-comparison')
def commercial_comparison(opportunity_id:int, data:CommercialComparisonIn, request:Request, db:Session=Depends(get_db)):
    auth(request,db); _commercial_context(db,opportunity_id)
    quotes=db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==opportunity_id).all()
    scenarios=db.query(LogisticsScenario).filter(LogisticsScenario.opportunity_id==opportunity_id, LogisticsScenario.is_active==True).all()
    if data.fx_rates:
        raise HTTPException(422,'ارسال نرخ ارز دستی مجاز نیست؛ FXRate منبع‌دار ثبت کنید.')
    currencies=[q.currency for q in quotes] + [s.currency for s in scenarios]
    fx, provenance=resolve_fx_map(db,currencies,data.base_currency)
    matrix=compare_supplier_routes(quotes,scenarios,quantity=data.quantity,base_currency=data.base_currency,fx_rates=fx)
    comparable=[x for x in matrix if x.get('comparable')]
    return {'base_currency':data.base_currency,'quantity':data.quantity,'quote_count':len(quotes),'scenario_count':len(scenarios),'comparable_count':len(comparable),'matrix':matrix,'ranked':comparable,'fx_provenance':provenance}

@router.post('/api/opportunities/{opportunity_id}/commercial-comparison/select')
def select_commercial_comparison(opportunity_id:int, data:CommercialComparisonSelectIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _commercial_context(db,opportunity_id)
    q=db.get(SupplierQuote,data.quote_id); s=db.get(LogisticsScenario,data.scenario_id)
    if not q or q.opportunity_id!=opportunity_id: raise HTTPException(404,'پیشنهاد تأمین‌کننده پیدا نشد.')
    if not s or s.opportunity_id!=opportunity_id: raise HTTPException(404,'سناریوی حمل پیدا نشد.')
    fx_rate, fx_row = resolve_fx_rate(db, q.currency, data.currency)
    # Build an offer using the selected supplier and route without double-counting route costs.
    base=CommercialOfferIn(supplier_quote_id=q.id,currency=data.currency,fx_rate_id=(fx_row.id if fx_row else None),exchange_rate=fx_rate,quantity=data.quantity,unit=data.unit,supplier_unit_price=q.unit_price,packaging_cost=0,inland_cost=0,export_cost=0,freight_cost=0,insurance_cost=0,customs_cost=0,other_cost=0,target_margin_percent=data.target_margin_percent,status=data.status,notes=data.notes,assumptions={'selected_quote_id':q.id,'selected_scenario_id':s.id})
    result=_build_offer(base,db)
    payload=base.model_dump(); payload.update(result); payload['logistics_scenario_id']=s.id; payload['incoterm']='CIF';
    for k in ['commission_amount','base_cost','fob_cost_before_margin']: payload.pop(k,None)
    offer=CommercialOffer(opportunity_id=opportunity_id,created_by=admin.id,**payload)
    db.add(offer); db.add(AuditLog(admin_id=admin.id,action='commercial_comparison_selected',entity_type='opportunity',entity_id=opportunity_id,details={'quote_id':q.id,'scenario_id':s.id}))
    db.commit(); db.refresh(offer)
    return {'offer':serialize(offer),'supplier_quote':serialize(q),'logistics_scenario':serialize(s),'calculation':result}

# V21.3 Market Price Intelligence
from ..services.market_intelligence import build_benchmark, compare_to_benchmark, build_price_trend, source_diversity, compare_supplier_quote_to_market

def _price_context(db, product_id:int):
    if not db.get(Product, product_id):
        raise HTTPException(404,'محصول پیدا نشد.')

def _unit_factor_map(raw:dict[str,float]):
    out={}
    for k,v in (raw or {}).items():
        if '->' in k:
            a,b=[x.strip() for x in k.split('->',1)]; out[(a,b)]=float(v)
        elif ':' in k:
            a,b=[x.strip() for x in k.split(':',1)]; out[(a,b)]=float(v)
    return out

@router.get('/api/market-prices/observations')
def market_price_observations(request:Request, product_id:int|None=None, market:str|None=None, db:Session=Depends(get_db)):
    auth(request,db)
    q=db.query(MarketPriceObservation)
    if product_id is not None: q=q.filter(MarketPriceObservation.product_id==product_id)
    if market: q=q.filter(MarketPriceObservation.market==market)
    rows=q.order_by(MarketPriceObservation.observed_at.desc()).limit(500).all()
    return [serialize(x) for x in rows]

@router.post('/api/market-prices/observations')
def create_market_price_observation(data:MarketPriceObservationIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _price_context(db,data.product_id)
    row=MarketPriceObservation(product_id=data.product_id, **data.model_dump(exclude={'product_id'}))
    if row.observed_at is None: row.observed_at=datetime.now(timezone.utc)
    db.add(row); db.add(AuditLog(admin_id=admin.id,action='market_price_observation_created',entity_type='market_price_observation',entity_id=0,details={'product_id':data.product_id,'market':data.market,'price':data.price,'currency':data.currency,'unit':data.unit}))
    db.commit(); db.refresh(row); return serialize(row)

@router.post('/api/market-prices/benchmark')
def calculate_market_price_benchmark(data:MarketBenchmarkIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); _price_context(db,data.product_id)
    q=db.query(MarketPriceObservation).filter(MarketPriceObservation.product_id==data.product_id,MarketPriceObservation.market==data.market)
    if data.country: q=q.filter(MarketPriceObservation.country==data.country)
    if data.grade: q=q.filter(MarketPriceObservation.grade==data.grade)
    # Do not filter by source unit here: benchmark normalization may convert units
    # when the operator supplies an explicit unit factor.
    if data.incoterm: q=q.filter(MarketPriceObservation.incoterm==data.incoterm)
    observations=q.order_by(MarketPriceObservation.observed_at.desc()).limit(500).all()
    
    if data.fx_rates:
        raise HTTPException(422,'ارسال نرخ ارز دستی مجاز نیست؛ نرخ‌ها باید از FXRate منبع‌دار خوانده شوند.')
    fx, fx_provenance = resolve_fx_map(db,[x.currency for x in observations],data.target_currency)
    result=build_benchmark(observations,target_currency=data.target_currency,target_unit=data.unit,fx_rates=fx,unit_factors=_unit_factor_map(data.unit_factors),min_effective=data.min_effective)
    existing=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id==data.product_id,MarketPriceBenchmark.market==data.market,MarketPriceBenchmark.country==data.country,MarketPriceBenchmark.grade==data.grade,MarketPriceBenchmark.unit==data.unit,MarketPriceBenchmark.incoterm==data.incoterm,MarketPriceBenchmark.currency==data.target_currency).order_by(MarketPriceBenchmark.created_at.desc()).first()
    payload={k:v for k,v in result.items() if k not in {'status','currency','unit'}}
    if existing:
        for k,v in payload.items(): setattr(existing,k,v)
        existing.benchmark_status=result['status']; existing.currency=data.target_currency; existing.unit=data.unit
        row=existing
    else:
        row=MarketPriceBenchmark(product_id=data.product_id,market=data.market,country=data.country,grade=data.grade,unit=data.unit,incoterm=data.incoterm,currency=data.target_currency,benchmark_status=result['status'],**payload)
        db.add(row)
    db.add(AuditLog(admin_id=admin.id,action='market_price_benchmark_built',entity_type='product',entity_id=data.product_id,details={'market':data.market,'observation_count':len(observations),'status':result['status']}))
    db.commit(); db.refresh(row)
    return {'benchmark':serialize(row),'observations_used':[serialize(x) for x in observations],'fx_provenance':fx_provenance}

@router.get('/api/market-prices/benchmarks')
def market_price_benchmarks(request:Request, product_id:int|None=None, market:str|None=None, db:Session=Depends(get_db)):
    auth(request,db); q=db.query(MarketPriceBenchmark)
    if product_id is not None: q=q.filter(MarketPriceBenchmark.product_id==product_id)
    if market: q=q.filter(MarketPriceBenchmark.market==market)
    return [serialize(x) for x in q.order_by(MarketPriceBenchmark.as_of.desc()).limit(200).all()]

@router.post('/api/market-prices/benchmarks/{benchmark_id}/compare')
def compare_market_price(benchmark_id:int, data:MarketBenchmarkCompareIn, request:Request, db:Session=Depends(get_db)):
    auth(request,db); b=db.get(MarketPriceBenchmark,benchmark_id)
    if not b: raise HTTPException(404,'Price Benchmark پیدا نشد.')
    
    if data.fx_rates:
        raise HTTPException(422,'ارسال نرخ ارز دستی مجاز نیست؛ نرخ‌ها باید از FXRate منبع‌دار خوانده شوند.')
    fx, provenance = resolve_fx_map(db,[data.currency,b.currency],b.currency)
    result=compare_to_benchmark(data.price,data.currency,data.unit,b,fx_rates=fx,unit_factors=_unit_factor_map(data.unit_factors))
    return {'benchmark':serialize(b),'comparison':result,'fx_provenance':provenance}

@router.get('/api/market-prices/trend')
def market_price_trend(request:Request, product_id:int, market:str, target_currency:str='USD', target_unit:str|None=None, country:str|None=None, grade:str|None=None, incoterm:str|None=None, days:int=90, unit_factors:str|None=None, db:Session=Depends(get_db)):
    auth(request,db); _price_context(db,product_id)
    days=max(1,min(days,3650)); cutoff=datetime.now(timezone.utc).timestamp()-days*86400
    q=db.query(MarketPriceObservation).filter(MarketPriceObservation.product_id==product_id,MarketPriceObservation.market==market)
    if country: q=q.filter(MarketPriceObservation.country==country)
    if grade: q=q.filter(MarketPriceObservation.grade==grade)
    if incoterm: q=q.filter(MarketPriceObservation.incoterm==incoterm)
    observations=[x for x in q.order_by(MarketPriceObservation.observed_at.asc()).limit(5000).all() if x.observed_at and x.observed_at.timestamp()>=cutoff]
    factors={}
    if unit_factors:
        for item in unit_factors.split(','):
            if ':' in item:
                a,b=item.split(':',1); factors[tuple(x.strip() for x in (a,b))]=1.0
    return {'product_id':product_id,'market':market,'days':days,'currency':target_currency,'unit':target_unit,'points':build_price_trend(observations,target_currency=target_currency,target_unit=target_unit,fx_rates={target_currency:1.0},unit_factors=factors),'observation_count':len(observations)}

@router.get('/api/market-prices/dashboard')
def market_price_dashboard(request:Request, product_id:int, market:str, target_currency:str='USD', target_unit:str='kg', country:str|None=None, grade:str|None=None, incoterm:str|None=None, days:int=90, db:Session=Depends(get_db)):
    auth(request,db); _price_context(db,product_id)
    q=db.query(MarketPriceObservation).filter(MarketPriceObservation.product_id==product_id,MarketPriceObservation.market==market)
    if country: q=q.filter(MarketPriceObservation.country==country)
    if grade: q=q.filter(MarketPriceObservation.grade==grade)
    if incoterm: q=q.filter(MarketPriceObservation.incoterm==incoterm)
    observations=q.order_by(MarketPriceObservation.observed_at.desc()).limit(5000).all()
    benchmarks=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id==product_id,MarketPriceBenchmark.market==market)
    if country: benchmarks=benchmarks.filter(MarketPriceBenchmark.country==country)
    if grade: benchmarks=benchmarks.filter(MarketPriceBenchmark.grade==grade)
    if incoterm: benchmarks=benchmarks.filter(MarketPriceBenchmark.incoterm==incoterm)
    benchmark=benchmarks.order_by(MarketPriceBenchmark.as_of.desc()).first()
    trust_scores={}
    source_ids={x.source_id for x in observations if x.source_id is not None}
    if source_ids:
        for st in db.query(SourceTrust).filter(SourceTrust.source_id.in_(source_ids)).all(): trust_scores[st.source_id]=st.overall_score
    diversity=source_diversity(observations,trust_scores)
    trend=build_price_trend(observations,target_currency=target_currency,target_unit=target_unit,fx_rates={target_currency:1.0},unit_factors={})
    alerts=[]
    if benchmark:
        center=benchmark.weighted_median_price or benchmark.median_price
        for o in observations[:100]:
            normalized,err=__import__('app.services.market_intelligence',fromlist=['normalize_price']).normalize_price(o.price,o.currency,o.unit,target_currency,target_unit,{target_currency:1.0},{})
            if normalized is not None and center>0:
                delta=(normalized-center)/center*100
                if abs(delta)>=10: alerts.append({'observation_id':o.id,'delta_pct':round(delta,2),'band':'Above Benchmark' if delta>0 else 'Below Benchmark'})
    return {'product_id':product_id,'market':market,'currency':target_currency,'unit':target_unit,'benchmark':serialize(benchmark) if benchmark else None,'observation_count':len(observations),'source_diversity':diversity,'trend':trend,'alerts':alerts[:20]}

@router.get('/api/opportunities/{opportunity_id}/intelligence')
def opportunity_intelligence_dashboard(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    """Return one mobile-ready, evidence-preserving view of the full opportunity chain."""
    auth(request,db)
    op=db.get(Opportunity, opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    manufacturer=db.get(Manufacturer,op.manufacturer_id)
    customer=db.get(Customer,op.customer_id)
    demand=db.get(Demand,op.demand_id) if op.demand_id else None
    product=db.get(Product,op.product_id)
    quotes=db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==opportunity_id).order_by(SupplierQuote.created_at.desc()).limit(20).all()
    offers=db.query(CommercialOffer).filter(CommercialOffer.opportunity_id==opportunity_id).order_by(CommercialOffer.created_at.desc()).limit(10).all()
    scenarios=db.query(LogisticsScenario).filter(LogisticsScenario.opportunity_id==opportunity_id).order_by(LogisticsScenario.created_at.desc()).limit(10).all()
    market_obj=db.get(Market,op.market_id) if op.market_id else None
    benchmark=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id==op.product_id,MarketPriceBenchmark.market==market_obj.name).order_by(MarketPriceBenchmark.as_of.desc()).first() if market_obj else None
    actions=db.query(OpportunityAction).filter(OpportunityAction.opportunity_id==opportunity_id).order_by(OpportunityAction.due_at.asc().nullslast(),OpportunityAction.created_at.desc()).limit(10).all()
    comparison_rows=[]
    if benchmark:
        for q in quotes:
            comparison_rows.append(compare_supplier_quote_to_market(q,benchmark,target_currency=benchmark.currency,target_unit=benchmark.unit,fx_rates={benchmark.currency:1.0},unit_factors={}))
    comparable=[x for x in comparison_rows if x.get('comparable')]
    best_quote=min(comparable,key=lambda x:x['normalized_landed_unit_cost']) if comparable else None
    return {
      'opportunity':serialize(op),
      'product':serialize(product) if product else None,
      'manufacturer':serialize(manufacturer) if manufacturer else None,
      'customer':serialize(customer) if customer else None,
      'demand':serialize(demand) if demand else None,
      'supplier_quotes':[serialize(x) for x in quotes],
      'market_benchmark':serialize(benchmark) if benchmark else None,
      'supplier_vs_market':comparison_rows,
      'best_comparable_quote':best_quote,
      'commercial_offers':[serialize(x) for x in offers],
      'logistics_scenarios':[serialize(x) for x in scenarios],
      'actions':[serialize(x) for x in actions],
      'chain_status':{
        'buyer': bool(customer), 'demand': bool(demand), 'supplier': bool(manufacturer),
        'quote': bool(quotes), 'benchmark': bool(benchmark), 'logistics': bool(scenarios),
        'commercial_offer': bool(offers), 'next_action': bool(op.next_action)
      },
      'disclaimer':'این صفحه ابزار تجمیع و تحلیل داده است؛ وجود Opportunity به معنی معامله قطعی نیست و تصمیم نهایی با کاربر است.'
    }

@router.post('/api/opportunities/{opportunity_id}/price-intelligence')
def opportunity_price_intelligence(opportunity_id:int, data:OpportunityPriceIntelligenceIn, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    opportunity=db.get(Opportunity, opportunity_id)
    if not opportunity: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    benchmark=db.get(MarketPriceBenchmark,data.benchmark_id) if data.benchmark_id else None
    if data.benchmark_id and (not benchmark or benchmark.product_id!=opportunity.product_id):
        raise HTTPException(400,'Benchmark انتخاب‌شده با محصول فرصت سازگار نیست.')
    if benchmark is None:
        market_obj=db.get(Market,opportunity.market_id) if opportunity.market_id else None
        benchmark=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id==opportunity.product_id,MarketPriceBenchmark.market==market_obj.name).order_by(MarketPriceBenchmark.as_of.desc()).first() if market_obj else None
    quotes=db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==opportunity_id).order_by(SupplierQuote.created_at.desc()).all()
    if data.fx_rates:
        raise HTTPException(422,'ارسال نرخ ارز دستی مجاز نیست؛ نرخ‌ها باید از FXRate منبع‌دار خوانده شوند.')
    fx, fx_provenance = resolve_fx_map(db,[q.currency for q in quotes] + ([benchmark.currency] if benchmark else []),data.target_currency)
    comparisons=[]
    if benchmark:
        for q in quotes:
            comparisons.append(compare_supplier_quote_to_market(q,benchmark,target_currency=data.target_currency,target_unit=data.target_unit,fx_rates=fx,unit_factors=data.unit_factors or {}))
    comparable=[x for x in comparisons if x.get('comparable')]
    return {'opportunity_id':opportunity_id,'product_id':opportunity.product_id,'benchmark':serialize(benchmark) if benchmark else None,'quote_count':len(quotes),'comparable_count':len(comparable),'comparisons':comparisons,'best_market_room':max(comparable,key=lambda x:x['market_room_per_unit']) if comparable else None,'assumptions':{'explicit_fx_only':True,'explicit_unit_conversion_only':True,'target_currency':data.target_currency,'target_unit':data.target_unit,'fx_provenance':fx_provenance}}


@router.post('/api/opportunities/{opportunity_id}/deal-decision')
def opportunity_deal_decision(opportunity_id:int, data:DealDecisionEngineIn, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    opportunity=db.get(Opportunity, opportunity_id)
    if not opportunity: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    quote=db.get(SupplierQuote,data.quote_id) if data.quote_id else db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==opportunity_id).order_by(SupplierQuote.created_at.desc()).first()
    if data.quote_id and (not quote or quote.opportunity_id!=opportunity_id): raise HTTPException(400,'Quote انتخاب‌شده متعلق به این فرصت نیست.')
    if not quote: raise HTTPException(404,'هیچ Supplier Quote برای این فرصت وجود ندارد.')
    benchmark=db.get(MarketPriceBenchmark,data.benchmark_id) if data.benchmark_id else None
    if data.benchmark_id and (not benchmark or benchmark.product_id!=opportunity.product_id): raise HTTPException(400,'Benchmark انتخاب‌شده با محصول فرصت سازگار نیست.')
    if benchmark is None:
        market_obj=db.get(Market,opportunity.market_id) if opportunity.market_id else None
        benchmark=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id==opportunity.product_id,MarketPriceBenchmark.market==market_obj.name).order_by(MarketPriceBenchmark.as_of.desc()).first() if market_obj else None
    if data.fx_rates:
        raise HTTPException(422,'ارسال نرخ ارز دستی مجاز نیست؛ نرخ‌ها باید از FXRate منبع‌دار خوانده شوند.')
    fx, fx_provenance = resolve_fx_map(db,[quote.currency] + ([benchmark.currency] if benchmark else []),data.target_currency)
    comparison=None
    landed=None
    if benchmark:
        comparison=compare_supplier_quote_to_market(quote,benchmark,target_currency=data.target_currency,target_unit=data.target_unit,fx_rates=fx,unit_factors=data.unit_factors or {})
        if comparison.get('comparable'): landed=comparison['normalized_landed_unit_cost']
    if landed is None:
        # Explicitly normalize the supplier quote even when no benchmark exists.
        from .services.market_intelligence import normalize_price
        landed,err=normalize_price(float(quote.unit_price),quote.currency,quote.unit,data.target_currency,data.target_unit,fx,data.unit_factors or {})
        if landed is None: raise HTTPException(400,f'Quote قابل مقایسه نیست: {err}')
        extras=(float(quote.freight_cost or 0)+float(quote.other_cost or 0))/float(quote.quantity or 1)
        extra,err=normalize_price(extras,quote.currency,quote.unit,data.target_currency,data.target_unit,fx,data.unit_factors or {})
        if extra is None: raise HTTPException(400,f'هزینه‌های جانبی قابل تبدیل نیست: {err}')
        landed+=extra
    benchmark_price=None
    if benchmark:
        benchmark_price=float(benchmark.weighted_median_price or benchmark.median_price or 0) or None
    result=deal_decision_engine(landed_unit_cost=landed,benchmark_unit_price=benchmark_price,target_margin_percent=data.target_margin_percent,minimum_margin_percent=data.minimum_margin_percent,selling_commission_percent=data.selling_commission_percent,selling_commission_fixed_per_unit=data.selling_commission_fixed_per_unit,quantity=data.quantity)
    return {'opportunity_id':opportunity_id,'quote':serialize(quote),'benchmark':serialize(benchmark) if benchmark else None,'comparison':comparison,'decision_engine':result,'disclaimer':'اعداد تحلیلی هستند و انتخاب یا تأیید معامله بر عهده کاربر است.','assumptions':{'explicit_fx_only':True,'explicit_unit_conversion_only':True}}


@router.post('/api/opportunities/{opportunity_id}/negotiation-intelligence')
def opportunity_negotiation_intelligence(opportunity_id:int, data:NegotiationIntelligenceIn, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    opportunity=db.get(Opportunity, opportunity_id)
    if not opportunity: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    quote=db.get(SupplierQuote,data.quote_id) if data.quote_id else db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==opportunity_id).order_by(SupplierQuote.created_at.desc()).first()
    if data.quote_id and (not quote or quote.opportunity_id!=opportunity_id): raise HTTPException(400,'Quote انتخاب‌شده متعلق به این فرصت نیست.')
    if not quote: raise HTTPException(404,'هیچ Supplier Quote برای این فرصت وجود ندارد.')
    benchmark=db.get(MarketPriceBenchmark,data.benchmark_id) if data.benchmark_id else None
    if data.benchmark_id and (not benchmark or benchmark.product_id!=opportunity.product_id): raise HTTPException(400,'Benchmark انتخاب‌شده با محصول فرصت سازگار نیست.')
    if benchmark is None:
        market_obj=db.get(Market,opportunity.market_id) if opportunity.market_id else None
        benchmark=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id==opportunity.product_id,MarketPriceBenchmark.market==market_obj.name).order_by(MarketPriceBenchmark.as_of.desc()).first() if market_obj else None
    from .services.market_intelligence import normalize_price
    if data.fx_rates:
        raise HTTPException(422,'ارسال نرخ ارز دستی مجاز نیست؛ نرخ‌ها باید از FXRate منبع‌دار خوانده شوند.')
    fx, fx_provenance = resolve_fx_map(db,[quote.currency] + ([benchmark.currency] if benchmark else []),data.target_currency); factors=data.unit_factors or {}
    base,err=normalize_price(float(quote.unit_price),quote.currency,quote.unit,data.target_currency,data.target_unit,fx,factors)
    if base is None: raise HTTPException(400,f'Quote قابل مقایسه نیست: {err}')
    extra_raw=(float(quote.freight_cost or 0)+float(quote.other_cost or 0))/float(quote.quantity or 1)
    extra,err=normalize_price(extra_raw,quote.currency,quote.unit,data.target_currency,data.target_unit,fx,factors)
    if extra is None: raise HTTPException(400,f'هزینه‌های جانبی قابل تبدیل نیست: {err}')
    landed=base+extra
    benchmark_price=None
    if benchmark:
        benchmark_price=float(benchmark.weighted_median_price or benchmark.median_price or 0) or None
        if benchmark.currency != data.target_currency or benchmark.unit != data.target_unit:
            benchmark_price,err=normalize_price(benchmark_price,benchmark.currency,benchmark.unit,data.target_currency,data.target_unit,fx,factors)
            if benchmark_price is None: raise HTTPException(400,f'Benchmark قابل تبدیل نیست: {err}')
    result=negotiation_engine(landed_unit_cost=landed,benchmark_unit_price=benchmark_price,target_margin_percent=data.target_margin_percent,minimum_margin_percent=data.minimum_margin_percent,selling_commission_percent=data.selling_commission_percent,selling_commission_fixed_per_unit=data.selling_commission_fixed_per_unit,opening_buffer_percent=data.opening_buffer_percent,concession_steps=(data.concession_steps or None),quantity=data.quantity)
    return {'opportunity_id':opportunity_id,'quote':serialize(quote),'benchmark':serialize(benchmark) if benchmark else None,'negotiation':result,'assumptions':{'explicit_fx_only':True,'explicit_unit_conversion_only':True,'target_currency':data.target_currency,'target_unit':data.target_unit,'fx_provenance':fx_provenance}}

# V21.9 Opportunity Workspace
@router.get('/api/opportunities/{opportunity_id}/workspace')
def opportunity_workspace(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    """Action-oriented workspace: one payload for the full opportunity operating context."""
    auth(request,db)
    op=db.get(Opportunity, opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    manufacturer=db.get(Manufacturer,op.manufacturer_id)
    customer=db.get(Customer,op.customer_id)
    demand=db.get(Demand,op.demand_id) if op.demand_id else None
    product=db.get(Product,op.product_id)
    quotes=db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==opportunity_id).order_by(SupplierQuote.created_at.desc()).limit(25).all()
    scenarios=db.query(LogisticsScenario).filter(LogisticsScenario.opportunity_id==opportunity_id,LogisticsScenario.is_active==True).order_by(LogisticsScenario.created_at.desc()).limit(25).all()
    offers=db.query(CommercialOffer).filter(CommercialOffer.opportunity_id==opportunity_id).order_by(CommercialOffer.created_at.desc()).limit(25).all()
    actions=db.query(OpportunityAction).filter(OpportunityAction.opportunity_id==opportunity_id).order_by(OpportunityAction.due_at.asc().nullslast(),OpportunityAction.created_at.desc()).limit(25).all()
    communications=db.query(CommunicationLog).filter(CommunicationLog.opportunity_id==opportunity_id).order_by(CommunicationLog.created_at.desc()).limit(25).all()
    rfqs=db.query(RFQDocument).filter(RFQDocument.opportunity_id==opportunity_id).order_by(RFQDocument.created_at.desc()).limit(25).all()
    market_obj=db.get(Market,op.market_id) if op.market_id else None
    benchmark=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id==op.product_id,MarketPriceBenchmark.market==market_obj.name).order_by(MarketPriceBenchmark.as_of.desc()).first() if market_obj else None
    comparison=[]
    if benchmark:
        for q in quotes:
            comparison.append(compare_supplier_quote_to_market(q,benchmark,target_currency=benchmark.currency,target_unit=benchmark.unit,fx_rates={benchmark.currency:1.0},unit_factors={}))
    open_actions=[x for x in actions if x.status not in ('Completed','Cancelled')]
    return {
        'opportunity':serialize(op),'product':serialize(product) if product else None,
        'manufacturer':serialize(manufacturer) if manufacturer else None,'customer':serialize(customer) if customer else None,
        'demand':serialize(demand) if demand else None,'benchmark':serialize(benchmark) if benchmark else None,
        'supplier_quotes':[serialize(x) for x in quotes],'supplier_vs_market':comparison,
        'logistics_scenarios':[serialize(x) for x in scenarios],'commercial_offers':[serialize(x) for x in offers],
        'actions':[serialize(x) for x in actions],'communications':[serialize(x) for x in communications],'rfqs':[serialize(x) for x in rfqs],
        'work_queue':{'open_actions':len(open_actions),'quotes':len(quotes),'routes':len(scenarios),'offers':len(offers),'communications':len(communications),'rfqs':len(rfqs)},
        'next_actions':[serialize(x) for x in open_actions[:5]],
        'disclaimer':'Workspace داده‌های عملیاتی و تحلیلی را یکجا می‌کند؛ Opportunity یا Benchmark به‌تنهایی به معنی معامله قطعی نیست.'
    }

@router.post('/api/opportunities/{opportunity_id}/workspace/command')
def opportunity_workspace_command(opportunity_id:int, data:OpportunityWorkspaceCommandIn, request:Request, db:Session=Depends(get_db)):
    """Create an operational record from the workspace using existing domain models."""
    admin=auth(request,db)
    if not db.get(Opportunity,opportunity_id): raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    created=None
    if data.command=='action':
        if not data.action: raise HTTPException(422,'action payload الزامی است.')
        created=OpportunityAction(opportunity_id=opportunity_id,created_by=admin.id,**data.action.model_dump())
        audit='workspace_action_created'
    elif data.command=='supplier_quote':
        if not data.supplier_quote: raise HTTPException(422,'supplier_quote payload الزامی است.')
        created=SupplierQuote(opportunity_id=opportunity_id,**data.supplier_quote.model_dump())
        audit='workspace_supplier_quote_created'
    elif data.command=='logistics_scenario':
        if not data.logistics_scenario: raise HTTPException(422,'logistics_scenario payload الزامی است.')
        created=LogisticsScenario(opportunity_id=opportunity_id,**data.logistics_scenario.model_dump())
        audit='workspace_logistics_created'
    else:
        if not data.communication: raise HTTPException(422,'communication payload الزامی است.')
        created=CommunicationLog(opportunity_id=opportunity_id,created_by=admin.id,**data.communication.model_dump())
        audit='workspace_communication_created'
    db.add(created); db.flush()
    db.add(AuditLog(admin_id=admin.id,action=audit,entity_type=data.command,entity_id=created.id,details={'opportunity_id':opportunity_id}))
    db.commit(); db.refresh(created)
    return {'status':'created','command':data.command,'record':serialize(created)}

# V22.0 Opportunity Operating System
OPPORTUNITY_STAGES = [
    'Discovered','Verified','Qualified','RFQ Sent','Supplier Quoted',
    'Logistics Priced','Commercial Offer','Negotiation','Won','Lost'
]
STAGE_CONFIG = {
    'Discovered': {'order':1,'terminal':False,'required_evidence':['opportunity']},
    'Verified': {'order':2,'terminal':False,'required_evidence':['customer_or_supplier_verification']},
    'Qualified': {'order':3,'terminal':False,'required_evidence':['demand_or_buyer_fit']},
    'RFQ Sent': {'order':4,'terminal':False,'required_evidence':['rfq_or_outbound_communication']},
    'Supplier Quoted': {'order':5,'terminal':False,'required_evidence':['supplier_quote']},
    'Logistics Priced': {'order':6,'terminal':False,'required_evidence':['logistics_scenario']},
    'Commercial Offer': {'order':7,'terminal':False,'required_evidence':['commercial_offer']},
    'Negotiation': {'order':8,'terminal':False,'required_evidence':['negotiation_or_follow_up']},
    'Won': {'order':9,'terminal':True,'required_evidence':['commercial_offer']},
    'Lost': {'order':10,'terminal':True,'required_evidence':['loss_reason']},
}

def _stage_evidence(db, op):
    counts = {
        'opportunity': 1,
        'customer_or_supplier_verification': int(bool(op.verification_status == 'Verified')),
        'demand_or_buyer_fit': int(bool(op.demand_id or op.customer_id)),
        'rfq_or_outbound_communication': db.query(RFQDocument).filter(RFQDocument.opportunity_id==op.id).count() + db.query(CommunicationLog).filter(CommunicationLog.opportunity_id==op.id, CommunicationLog.direction=='outbound').count(),
        'supplier_quote': db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==op.id).count(),
        'logistics_scenario': db.query(LogisticsScenario).filter(LogisticsScenario.opportunity_id==op.id, LogisticsScenario.is_active==True).count(),
        'commercial_offer': db.query(CommercialOffer).filter(CommercialOffer.opportunity_id==op.id).count(),
        'negotiation_or_follow_up': db.query(OpportunityAction).filter(OpportunityAction.opportunity_id==op.id, OpportunityAction.action_type.in_(['follow_up','meeting','call','whatsapp','email'])).count(),
        'loss_reason': int(bool(op.lost_reason and op.lost_reason.strip())),
    }
    return counts

@router.get('/api/opportunities/stages')
def opportunity_stage_config(request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    return [{'stage':s, **STAGE_CONFIG[s]} for s in OPPORTUNITY_STAGES]

@router.get('/api/opportunities/pipeline')
def opportunity_pipeline(request:Request, db:Session=Depends(get_db), include_archived:bool=False):
    auth(request,db)
    q=db.query(Opportunity)
    if not include_archived:
        q=q.filter(Opportunity.is_archived==False)
    rows=q.order_by(Opportunity.stage_updated_at.desc()).all()
    now=datetime.now(timezone.utc)
    by_stage={s:[] for s in OPPORTUNITY_STAGES}
    for op in rows:
        stage=op.opportunity_stage if op.opportunity_stage in STAGE_CONFIG else 'Discovered'
        item=serialize(op)
        item['overdue']=bool(op.stage_due_at and op.stage_due_at < now and stage not in ('Won','Lost'))
        item['days_in_stage']=max(0,(now-op.stage_updated_at).total_seconds()/86400) if op.stage_updated_at else None
        item['owner']=serialize(db.get(Admin,op.stage_owner_id)) if op.stage_owner_id else None
        by_stage[stage].append(item)
    return {'stages':by_stage,'counts':{s:len(v) for s,v in by_stage.items()},'total':len(rows)}

@router.get('/api/opportunities/{opportunity_id}/operating-system')
def opportunity_operating_system(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    stage=op.opportunity_stage if op.opportunity_stage in STAGE_CONFIG else 'Discovered'
    evidence=_stage_evidence(db,op)
    next_stage=None
    if stage not in ('Won','Lost'):
        idx=OPPORTUNITY_STAGES.index(stage)
        next_stage=OPPORTUNITY_STAGES[idx+1] if idx+1 < len(OPPORTUNITY_STAGES) else None
    open_actions=db.query(OpportunityAction).filter(OpportunityAction.opportunity_id==opportunity_id,OpportunityAction.status.notin_(['Completed','Cancelled'])).order_by(OpportunityAction.due_at.asc().nullslast()).limit(10).all()
    return {'opportunity':serialize(op),'stage':stage,'stage_config':STAGE_CONFIG[stage],'evidence':evidence,'next_stage':next_stage,'open_actions':[serialize(x) for x in open_actions],'overdue':bool(op.stage_due_at and op.stage_due_at < datetime.now(timezone.utc) and stage not in ('Won','Lost')),'disclaimer':'Pipeline وضعیت عملیاتی فرصت را ثبت می‌کند؛ مرحله Won به معنی ثبت نتیجه کاربر است و تضمین وصول یا قرارداد نیست.'}

@router.post('/api/opportunities/{opportunity_id}/stage')
def transition_opportunity_stage(opportunity_id:int, data:OpportunityStageTransitionIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    old=op.opportunity_stage if op.opportunity_stage in STAGE_CONFIG else 'Discovered'
    new=data.stage
    if old in ('Won','Lost') and new != old:
        raise HTTPException(409,'فرصت بسته شده است و بدون بازگشایی صریح قابل تغییر مرحله نیست.')
    evidence=_stage_evidence(db,op)
    required=STAGE_CONFIG[new]['required_evidence']
    missing=[x for x in required if not evidence.get(x)]
    if missing and new not in ('Lost','Won'):
        raise HTTPException(422,detail={'message':'مدارک لازم برای ورود به این مرحله کامل نیست.','missing':missing,'evidence':evidence})
    if new=='Lost' and not (data.reason or '').strip():
        raise HTTPException(422,'برای مرحله Lost ثبت دلیل توقف الزامی است.')
    if data.owner_id is not None and not db.get(Admin,data.owner_id):
        raise HTTPException(400,'مسئول انتخاب‌شده وجود ندارد.')
    now=datetime.now(timezone.utc)
    op.opportunity_stage=new
    op.stage_updated_at=now
    op.stage_due_at=data.due_at
    op.stage_owner_id=data.owner_id
    op.stage_reason=data.reason
    if data.next_action is not None: op.next_action=data.next_action
    if new=='Lost':
        op.lost_reason=data.reason
        op.closed_at=now
    elif new=='Won':
        op.lost_reason=None
        op.closed_at=now
    else:
        op.closed_at=None
        op.lost_reason=None
    db.add(AuditLog(admin_id=admin.id,action='opportunity_stage_changed',entity_type='opportunity',entity_id=op.id,details={'from':old,'to':new,'reason':data.reason,'due_at':data.due_at.isoformat() if data.due_at else None,'owner_id':data.owner_id}))
    db.commit(); db.refresh(op)
    return {'status':'ok','opportunity':serialize(op),'transition':{'from':old,'to':new},'evidence':_stage_evidence(db,op)}

# V22.1 Automation & Follow-up Engine
from ..services.automation import run_automation, build_automation_plan

@router.get('/api/automation/plan')
def automation_plan(request:Request, opportunity_id:int|None=None, db:Session=Depends(get_db)):
    auth(request,db)
    from .models import Opportunity
    q=db.query(Opportunity).filter(Opportunity.is_archived==False, Opportunity.opportunity_stage.notin_(['Won','Lost']))
    if opportunity_id is not None: q=q.filter(Opportunity.id==opportunity_id)
    rows=[]
    for op in q.order_by(Opportunity.stage_updated_at.asc()).all():
        rows.extend([{'opportunity_id':op.id,'opportunity_stage':op.opportunity_stage,**x} for x in build_automation_plan(db,op)])
    return {'dry_run':True,'count':len(rows),'items':rows}

@router.post('/api/automation/run')
def automation_run(request:Request, opportunity_id:int|None=None, dry_run:bool=False, db:Session=Depends(get_db)):
    admin=auth(request,db)
    items=run_automation(db,admin_id=admin.id,opportunity_id=opportunity_id,dry_run=dry_run)
    return {'status':'ok','dry_run':dry_run,'created_count':len(items),'items':items,'message':'Automation plan generated.' if dry_run else 'Automation actions created.'}

@router.get('/api/automation/overdue')
def automation_overdue(request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    from .models import Opportunity
    now=datetime.now(timezone.utc)
    rows=db.query(Opportunity).filter(Opportunity.is_archived==False,Opportunity.stage_due_at < now,Opportunity.opportunity_stage.notin_(['Won','Lost'])).order_by(Opportunity.stage_due_at.asc()).limit(200).all()
    return {'count':len(rows),'items':[{'opportunity':serialize(x),'overdue_hours':round((now-x.stage_due_at).total_seconds()/3600,1)} for x in rows]}

# V22.2 Opportunity Health & Smart Scoring
@router.get('/api/opportunities/{opportunity_id}/health')
def opportunity_health(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    op=db.get(Opportunity, opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    return calculate_opportunity_health(db, op)

@router.get('/api/opportunities/health')
def opportunities_health(request:Request, db:Session=Depends(get_db), min_health:float=0, limit:int=100):
    auth(request,db)
    rows=db.query(Opportunity).filter(Opportunity.is_archived==False).order_by(Opportunity.stage_updated_at.asc()).limit(min(limit,200)).all()
    items=[]
    for op in rows:
        h=calculate_opportunity_health(db,op)
        if h['overall_health'] >= min_health: items.append(h)
    items.sort(key=lambda x:(x['overall_health'], x['urgency']))
    return {'count':len(items),'items':items}

@router.get('/api/opportunities/{opportunity_id}/health/actions')
def opportunity_health_actions(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    op=db.get(Opportunity, opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    h=calculate_opportunity_health(db,op)
    actions=[]
    if h['verification_score'] < 60: actions.append({'priority':'high','action':'Verify buyer/supplier','reason':'اعتبارسنجی ناکافی'})
    if h['counts']['quotes']==0: actions.append({'priority':'high','action':'Request supplier quote','reason':'Quote ثبت نشده است'})
    if h['counts']['routes']==0 and op.opportunity_stage in {'Supplier Quoted','Logistics Priced','Commercial Offer','Negotiation'}: actions.append({'priority':'medium','action':'Price logistics','reason':'سناریوی حمل وجود ندارد'})
    if h['counts']['overdue_actions']: actions.append({'priority':'high','action':'Clear overdue follow-up','reason':'اقدام معوق وجود دارد'})
    if h['days_in_stage'] > {'Discovered':2,'Verified':3,'Qualified':3,'RFQ Sent':3,'Supplier Quoted':3,'Logistics Priced':3,'Commercial Offer':3,'Negotiation':5}.get(op.opportunity_stage,999): actions.append({'priority':'medium','action':'Advance or requalify stage','reason':'فرصت در مرحله بیش از زمان استاندارد مانده است'})
    return {'opportunity_id':opportunity_id,'health':h,'recommended_actions':actions}


# V22.4 Source & Evidence Intelligence
from ..services.source_evidence import opportunity_source_intelligence

@router.get('/api/opportunities/{opportunity_id}/source-intelligence')
def opportunity_source_intelligence_endpoint(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    return opportunity_source_intelligence(db,op)

@router.get('/api/source-intelligence/opportunities')
def source_intelligence_opportunities(request:Request, db:Session=Depends(get_db), limit:int=100):
    auth(request,db)
    rows=db.query(Opportunity).filter(Opportunity.is_archived==False).order_by(Opportunity.stage_updated_at.asc()).limit(min(limit,200)).all()
    items=[opportunity_source_intelligence(db,op) for op in rows]
    items.sort(key=lambda x:(x['overall_score'], x['conflict_count']))
    return {'count':len(items),'items':items}

@router.get('/api/opportunities/{opportunity_id}/source-intelligence/conflicts')
def opportunity_source_conflicts(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    data=opportunity_source_intelligence(db,op)
    return {'opportunity_id':opportunity_id,'conflict_count':data['conflict_count'],'conflicts':data['conflicts']}

# V22.3 Smart Data Quality & Verification Center
from ..services.data_quality import opportunity_data_quality

@router.get('/api/data-quality/opportunities')
def data_quality_opportunities(request:Request, db:Session=Depends(get_db), status:str|None=None, limit:int=100):
    auth(request,db)
    rows=db.query(Opportunity).filter(Opportunity.is_archived==False).order_by(Opportunity.stage_updated_at.asc()).limit(min(limit,200)).all()
    items=[opportunity_data_quality(db,op) for op in rows]
    if status: items=[x for x in items if x['status'].lower()==status.lower()]
    return {'count':len(items),'items':items}

@router.get('/api/opportunities/{opportunity_id}/data-quality')
def opportunity_data_quality_endpoint(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    return opportunity_data_quality(db,op)

@router.get('/api/opportunities/{opportunity_id}/data-quality/gate')
def opportunity_data_quality_gate(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    q=opportunity_data_quality(db,op)
    return {'opportunity_id':opportunity_id,'can_advance':q['gate']['can_advance'],'blockers':q['blockers'],'warnings':q['warnings'],'score':q['overall_score']}


# V22.5 Temporal Market & Opportunity Intelligence
from ..services.temporal_intelligence import opportunity_temporal_intelligence, market_price_trend

@router.get('/api/opportunities/{opportunity_id}/temporal-intelligence')
def opportunity_temporal_intelligence_endpoint(opportunity_id:int, request:Request, db:Session=Depends(get_db), days:int=90):
    auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    return opportunity_temporal_intelligence(db,op,days=max(7,min(days,3650)))

@router.get('/api/temporal-intelligence/opportunities')
def temporal_intelligence_opportunities(request:Request, db:Session=Depends(get_db), days:int=90, limit:int=100):
    auth(request,db)
    rows=db.query(Opportunity).filter(Opportunity.is_archived==False).order_by(Opportunity.stage_updated_at.asc()).limit(min(limit,200)).all()
    items=[opportunity_temporal_intelligence(db,op,days=max(7,min(days,3650))) for op in rows]
    items.sort(key=lambda x:x['temporal_score'])
    return {'count':len(items),'items':items}

# Canonical GET /api/market-prices/trend route is defined above; duplicate removed.

# V22.6 Cross-Source Change Detection
from ..services.change_detection import detect_opportunity_changes

@router.get('/api/opportunities/{opportunity_id}/change-intelligence')
def opportunity_change_intelligence(opportunity_id:int, request:Request, db:Session=Depends(get_db), days:int=180, persist:bool=False):
    admin=auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    result=detect_opportunity_changes(db,op,days=max(7,min(days,3650)),persist=persist)
    if persist and result['persisted_events']:
        result['audit_admin_id']=admin.id
    return result

@router.get('/api/change-intelligence/opportunities')
def change_intelligence_opportunities(request:Request, db:Session=Depends(get_db), days:int=180, limit:int=100, persist:bool=False):
    auth(request,db)
    rows=db.query(Opportunity).filter(Opportunity.is_archived==False).order_by(Opportunity.stage_updated_at.asc()).limit(min(limit,200)).all()
    items=[detect_opportunity_changes(db,op,days=max(7,min(days,3650)),persist=persist) for op in rows]
    items.sort(key=lambda x:(x['high_events'],x['medium_events']),reverse=True)
    return {'count':len(items),'items':items}

@router.get('/api/opportunities/{opportunity_id}/change-intelligence/audit')
def opportunity_change_audit(opportunity_id:int, request:Request, db:Session=Depends(get_db), limit:int=100):
    auth(request,db)
    op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    rows=db.query(AuditLog).filter(AuditLog.action=='source_change_detected',AuditLog.entity_type=='opportunity',AuditLog.entity_id==opportunity_id).order_by(AuditLog.created_at.desc()).limit(min(limit,200)).all()
    return {'opportunity_id':opportunity_id,'count':len(rows),'events':[{'id':x.id,'created_at':x.created_at.isoformat() if x.created_at else None,'details':x.details} for x in rows]}

# V22.7 Intelligence Alert & Watchtower
from ..services.watchtower import plan_watchtower, persist_alerts

@router.get('/api/watchtower/plan')
def watchtower_plan(request:Request, db:Session=Depends(get_db), days:int=180, limit:int=200):
    auth(request,db)
    return plan_watchtower(db,max(7,min(days,3650)),min(limit,500))

@router.post('/api/watchtower/run')
def watchtower_run(request:Request, db:Session=Depends(get_db), days:int=180, limit:int=200):
    admin=auth(request,db)
    plan=plan_watchtower(db,max(7,min(days,3650)),min(limit,500))
    saved=persist_alerts(db,plan['items'],admin.id)
    return {**plan,'persisted':saved}

@router.get('/api/watchtower/alerts')
def watchtower_alerts(request:Request, db:Session=Depends(get_db), status:str='New', severity:str|None=None, limit:int=100):
    auth(request,db)
    q=db.query(AlertEvent).filter(AlertEvent.status==status)
    if severity: q=q.filter(AlertEvent.severity==severity)
    rows=q.order_by(AlertEvent.last_seen_at.desc()).limit(min(limit,200)).all()
    return {'count':len(rows),'items':[{'id':x.id,'opportunity_id':x.opportunity_id,'alert_type':x.alert_type,'severity':x.severity,'status':x.status,'message':x.message,'reason':x.reason,'first_seen_at':x.first_seen_at.isoformat(),'last_seen_at':x.last_seen_at.isoformat(),'payload':x.payload} for x in rows]}

@router.post('/api/watchtower/alerts/{alert_id}/acknowledge')
def acknowledge_alert(alert_id:int, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); row=db.get(AlertEvent,alert_id)
    if not row: raise HTTPException(404,'هشدار پیدا نشد.')
    row.status='Acknowledged'; row.acknowledged_at=datetime.now(timezone.utc); row.updated_at=datetime.now(timezone.utc); db.commit()
    return {'id':row.id,'status':row.status,'admin_id':admin.id}

@router.post('/api/watchtower/alerts/{alert_id}/resolve')
def resolve_alert(alert_id:int, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); row=db.get(AlertEvent,alert_id)
    if not row: raise HTTPException(404,'هشدار پیدا نشد.')
    row.status='Resolved'; row.resolved_at=datetime.now(timezone.utc); row.updated_at=datetime.now(timezone.utc); db.commit()
    return {'id':row.id,'status':row.status,'admin_id':admin.id}

# V22.8 Command Center & Executive Dashboard
from ..services.command_center import command_center_summary, command_center_opportunities, command_center_alerts

@router.get('/api/command-center/summary')
def command_center_summary_endpoint(request:Request, db:Session=Depends(get_db), product_id:int|None=None, market:str|None=None, stage:str|None=None):
    auth(request,db)
    return command_center_summary(db,product_id=product_id,market=market,stage=stage)

@router.get('/api/command-center/opportunities')
def command_center_opportunities_endpoint(request:Request, db:Session=Depends(get_db), product_id:int|None=None, market:str|None=None, stage:str|None=None, severity:str|None=None, limit:int=50):
    auth(request,db)
    return command_center_opportunities(db,product_id=product_id,market=market,stage=stage,severity=severity,limit=min(limit,200))

@router.get('/api/command-center/alerts')
def command_center_alerts_endpoint(request:Request, db:Session=Depends(get_db), product_id:int|None=None, market:str|None=None, status:str='New', severity:str|None=None, limit:int=100):
    auth(request,db)
    return command_center_alerts(db,product_id=product_id,market=market,status=status,severity=severity,limit=min(limit,200))

# V23.3 Import Cost & Duty Intelligence
@router.get('/api/import-cost-rules')
def import_cost_rules_list(request:Request, db:Session=Depends(get_db), market_id:int|None=None, hs_code:str|None=None, status:str|None=None):
    auth(request,db); q=db.query(ImportCostRule)
    if market_id is not None: q=q.filter(ImportCostRule.market_id==market_id)
    if hs_code: q=q.filter(ImportCostRule.hs_code==hs_code)
    if status: q=q.filter(ImportCostRule.status==status)
    return [serialize_import_rule(x) for x in q.order_by(ImportCostRule.updated_at.desc()).limit(200).all()]

@router.post('/api/import-cost-rules')
def import_cost_rule_create(data:ImportCostRuleIn, request:Request, db:Session=Depends(get_db)):
    admin=require_permission(request,db,'market_rules.write')
    if not db.get(Market,data.market_id): raise HTTPException(404,'بازار پیدا نشد.')
    if data.status not in IMPORT_COST_STATUSES: raise HTTPException(400,'وضعیت Rule نامعتبر است.')
    x=ImportCostRule(**data.model_dump(),retrieved_at=datetime.now(timezone.utc)); db.add(x); db.flush(); audit(db,admin,'import_cost_rule.created','ImportCostRule',x.id,{'market_id':x.market_id,'hs_code':x.hs_code,'status':x.status}); db.commit(); db.refresh(x); return serialize_import_rule(x)

@router.post('/api/import-cost-rules/{rule_id}/calculate')
def import_cost_rule_calculate(rule_id:int, data:ImportCostCalculateIn, request:Request, db:Session=Depends(get_db)):
    auth(request,db); r=db.get(ImportCostRule,rule_id)
    if not r: raise HTTPException(404,'Import Cost Rule پیدا نشد.')
    if not __import__('app.services.import_cost',fromlist=['is_current']).is_current(r): raise HTTPException(409,'این Rule تأییدشده و جاری نیست؛ محاسبه قانونی انجام نمی‌شود.')
    return {'status':'calculated','rule':serialize_import_rule(r),'calculation':calculate_import_cost(r,data.customs_value,data.quantity,data.include_fixed_fee),'disclaimer':'این محاسبه فقط بر اساس Rule تأییدشده ذخیره‌شده انجام شده است؛ نرخ یا الزام قانونی جدیدی استنباط نمی‌شود.'}

@router.post('/api/products/{product_id}/markets/{market_id}/import-cost')
def product_import_cost(product_id:int, market_id:int, data:ImportCostCalculateIn, request:Request, db:Session=Depends(get_db), hs_code:str|None=None):
    auth(request,db); p=db.get(Product,product_id); m=db.get(Market,market_id)
    if not p or not m: raise HTTPException(404,'محصول یا بازار پیدا نشد.')
    if not hs_code:
        pc=db.query(ProductCompliance).filter(ProductCompliance.product_id==product_id,ProductCompliance.market_id==market_id,ProductCompliance.status=='Verified').order_by(ProductCompliance.updated_at.desc()).first()
        hs_code=pc.hs_code if pc else None
    if not hs_code: return {'status':'Blocked','reason':'No verified HS classification is available.','product_id':product_id,'market_id':market_id}
    rule=find_verified_rule(db,market_id,hs_code,p.name)
    if not rule: return {'status':'Needs Verification','reason':'No current verified import-cost rule is available for this HS code.','hs_code':hs_code,'product_id':product_id,'market_id':market_id}
    return {'status':'Ready','product_id':product_id,'market_id':market_id,'hs_code':hs_code,'rule':serialize_import_rule(rule),'calculation':calculate_import_cost(rule,data.customs_value,data.quantity,data.include_fixed_fee)}

@router.post('/api/opportunities/{opportunity_id}/import-cost')
def opportunity_import_cost(opportunity_id:int, data:ImportCostCalculateIn, request:Request, db:Session=Depends(get_db), hs_code:str|None=None):
    auth(request,db); op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت پیدا نشد.')
    if not op.market_id: return {'status':'Blocked','reason':'Opportunity has no market mapping.'}
    p=db.get(Product,op.product_id); m=db.get(Market,op.market_id)
    if not p or not m: raise HTTPException(404,'محصول یا بازار فرصت پیدا نشد.')
    if not hs_code:
        pc=db.query(ProductCompliance).filter(ProductCompliance.product_id==p.id,ProductCompliance.market_id==m.id,ProductCompliance.status=='Verified').order_by(ProductCompliance.updated_at.desc()).first(); hs_code=pc.hs_code if pc else None
    if not hs_code: return {'status':'Blocked','reason':'No verified HS classification is available.','opportunity_id':opportunity_id}
    rule=find_verified_rule(db,m.id,hs_code,p.name)
    if not rule: return {'status':'Needs Verification','reason':'No current verified import-cost rule is available for this HS code.','opportunity_id':opportunity_id,'hs_code':hs_code}
    return {'status':'Ready','opportunity_id':opportunity_id,'market_id':m.id,'product_id':p.id,'hs_code':hs_code,'rule':serialize_import_rule(rule),'calculation':calculate_import_cost(rule,data.customs_value,data.quantity,data.include_fixed_fee),'disclaimer':'Customs value must be supplied explicitly; freight, insurance and FX are not inferred by this endpoint.'}

@router.post('/api/opportunities/{opportunity_id}/commercial-offers/{offer_id}/apply-import-cost')
def apply_import_cost_to_offer(opportunity_id:int, offer_id:int, data:ImportCostCalculateIn, request:Request, db:Session=Depends(get_db), hs_code:str|None=None):
    admin=auth(request,db); _commercial_context(db,opportunity_id)
    offer=db.get(CommercialOffer,offer_id)
    if not offer or offer.opportunity_id!=opportunity_id: raise HTTPException(404,'پیشنهاد تجاری پیدا نشد.')
    op=db.get(Opportunity,opportunity_id); p=db.get(Product,op.product_id) if op else None; market=db.get(Market,op.market_id) if op and op.market_id else None
    if not p or not market: raise HTTPException(400,'فرصت فاقد محصول یا بازار معتبر است.')
    if not hs_code:
        pc=db.query(ProductCompliance).filter(ProductCompliance.product_id==p.id,ProductCompliance.market_id==market.id,ProductCompliance.status=='Verified').order_by(ProductCompliance.updated_at.desc()).first(); hs_code=pc.hs_code if pc else None
    if not hs_code: raise HTTPException(409,'HS Code تأییدشده موجود نیست.')
    rule=find_verified_rule(db,market.id,hs_code,p.name)
    if not rule: raise HTTPException(409,'Import Cost Rule تأییدشده و جاری موجود نیست.')
    calc=calculate_import_cost(rule,data.customs_value,data.quantity,data.include_fixed_fee)
    offer.customs_cost=calc['total_import_taxes_and_fees']
    offer.assumptions={**(offer.assumptions or {}),'import_cost_rule_id':rule.id,'import_cost_hs_code':hs_code,'import_cost_calculation':calc,'customs_value':data.customs_value}
    # Recalculate the commercial offer with the verified import cost while preserving explicit logistics inputs.
    payload={k:getattr(offer,k) for k in ['quantity','unit','supplier_unit_price','packaging_cost','inland_cost','export_cost','freight_cost','insurance_cost','customs_cost','other_cost','commission_percent','commission_fixed','target_margin_percent','status','notes','logistics_scenario_id','incoterm','currency','exchange_rate'] if hasattr(offer,k)}
    payload.update({'quantity':offer.quantity,'unit':offer.unit,'supplier_unit_price':offer.supplier_unit_price,'packaging_cost':offer.packaging_cost,'inland_cost':offer.inland_cost,'export_cost':offer.export_cost,'freight_cost':offer.freight_cost,'insurance_cost':offer.insurance_cost,'customs_cost':offer.customs_cost,'other_cost':offer.other_cost,'commission_percent':offer.commission_percent,'commission_fixed':offer.commission_fixed,'target_margin_percent':offer.target_margin_percent,'status':offer.status,'notes':offer.notes,'logistics_scenario_id':None,'incoterm':offer.incoterm})
    calc_offer=calculate_offer(type('OfferInput',(),payload)())
    for k,v in calc_offer.items():
        if hasattr(offer,k): setattr(offer,k,v)
    db.add(AuditLog(admin_id=admin.id,action='commercial_offer.import_cost_applied',entity_type='commercial_offer',entity_id=offer.id,details={'rule_id':rule.id,'hs_code':hs_code,'customs_value':data.customs_value,'import_cost':calc['total_import_taxes_and_fees']})); db.commit(); db.refresh(offer)
    return {'offer':serialize(offer),'import_cost_rule':serialize_import_rule(rule),'import_cost':calc,'commercial_recalculation':calc_offer}

# V23.2 HS Code & Product Compliance Intelligence
@router.get('/api/product-compliance')
def product_compliance_list(request:Request, db:Session=Depends(get_db), product_id:int|None=None, market_id:int|None=None, hs_code:str|None=None):
    auth(request,db); q=db.query(ProductCompliance)
    if product_id is not None: q=q.filter(ProductCompliance.product_id==product_id)
    if market_id is not None: q=q.filter(ProductCompliance.market_id==market_id)
    if hs_code: q=q.filter(ProductCompliance.hs_code==hs_code)
    return [serialize_compliance(x) for x in q.order_by(ProductCompliance.updated_at.desc()).limit(200).all()]

@router.post('/api/product-compliance')
def product_compliance_create(data:ProductComplianceIn, request:Request, db:Session=Depends(get_db)):
    admin=require_permission(request,db,'market_rules.write')
    if not db.get(Product,data.product_id) or not db.get(Market,data.market_id): raise HTTPException(404,'محصول یا بازار پیدا نشد.')
    if data.status not in COMPLIANCE_STATUSES: raise HTTPException(400,'وضعیت طبقه‌بندی نامعتبر است.')
    x=ProductCompliance(**data.model_dump()); db.add(x); db.flush(); audit(db,admin,'product_compliance.created','ProductCompliance',x.id,{'product_id':x.product_id,'market_id':x.market_id,'hs_code':x.hs_code}); db.commit(); db.refresh(x); return serialize_compliance(x)

@router.post('/api/compliance-requirements')
def compliance_requirement_create(data:ComplianceRequirementIn, request:Request, db:Session=Depends(get_db)):
    admin=require_permission(request,db,'market_rules.write')
    if not db.get(ProductCompliance,data.product_compliance_id): raise HTTPException(404,'طبقه‌بندی محصول پیدا نشد.')
    if data.status not in COMPLIANCE_STATUSES or data.requirement_type not in REQ_TYPES: raise HTTPException(400,'وضعیت یا نوع الزام نامعتبر است.')
    x=ComplianceRequirement(**data.model_dump()); db.add(x); db.flush(); audit(db,admin,'compliance_requirement.created','ComplianceRequirement',x.id,{'product_compliance_id':x.product_compliance_id}); db.commit(); db.refresh(x); return serialize_requirement(x)

@router.get('/api/products/{product_id}/markets/{market_id}/compliance-gate')
def product_compliance_gate(product_id:int, market_id:int, request:Request, db:Session=Depends(get_db), hs_code:str|None=None):
    auth(request,db); p=db.get(Product,product_id); m=db.get(Market,market_id)
    if not p or not m: raise HTTPException(404,'محصول یا بازار پیدا نشد.')
    return compliance_gate(db,p,m,hs_code)

@router.get('/api/opportunities/{opportunity_id}/compliance-gate')
def opportunity_compliance_gate(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db); op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت پیدا نشد.')
    p=db.get(Product,op.product_id); m=db.get(Market,op.market_id) if op.market_id else None
    if not p or not m: return {'status':'Blocked','reason':'Opportunity is missing product or market mapping.','opportunity_id':opportunity_id}
    return {'opportunity_id':opportunity_id,**compliance_gate(db,p,m)}

# V23.4 Landed Cost & Total Import Cost Engine
from ..services.landed_cost import calculate_total_landed_cost

@router.post('/api/opportunities/{opportunity_id}/landed-cost')
def opportunity_landed_cost(opportunity_id:int, data:LandedCostIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت پیدا نشد.')
    import_result=None; rule=None; hs=data.hs_code
    if data.import_cost_rule_id:
        rule=db.get(ImportCostRule,data.import_cost_rule_id)
        if not rule: raise HTTPException(404,'Import Cost Rule پیدا نشد.')
        if not __import__('app.services.import_cost',fromlist=['is_current']).is_current(rule): raise HTTPException(409,'Import Cost Rule تأییدشده و جاری نیست.')
    elif op.market_id and op.product_id:
        p=db.get(Product,op.product_id)
        if not hs:
            pc=db.query(ProductCompliance).filter(ProductCompliance.product_id==op.product_id,ProductCompliance.market_id==op.market_id,ProductCompliance.status=='Verified').order_by(ProductCompliance.updated_at.desc()).first()
            hs=pc.hs_code if pc else None
        if hs: rule=find_verified_rule(db,op.market_id,hs,p.name if p else None)
    if rule:
        if rule.currency != data.currency and data.fx_rate is None:
            raise HTTPException(409,'برای تبدیل ارز Import Rule به ارز Landed Cost باید FX Rate صریح ارائه شود.')
        cv=data.customs_value
        if cv is None: raise HTTPException(400,'customs_value برای محاسبه حقوق ورودی باید صراحتاً ارائه شود.')
        import_result=calculate_import_cost(rule,cv,data.quantity,True)
    elif data.customs_value is not None:
        raise HTTPException(409,'برای customs_value ابتدا یک Import Cost Rule تأییدشده و جاری لازم است.')
    result=calculate_total_landed_cost(quantity=data.quantity,unit=data.unit,currency=data.currency,supplier_cost=data.supplier_cost,packaging_cost=data.packaging_cost,inland_cost=data.inland_cost,export_cost=data.export_cost,freight_cost=data.freight_cost,insurance_cost=data.insurance_cost,customs_value=data.customs_value,import_cost=import_result,destination_handling=data.destination_handling,other_cost=data.other_cost,fx_rate=data.fx_rate,expected_currency=rule.currency if rule else None)
    result.update({'opportunity_id':opportunity_id,'hs_code':hs,'import_cost_rule_id':rule.id if rule else None,'fx_required':bool(rule and rule.currency!=data.currency),'disclaimer':'این موتور فقط هزینه‌های صریحاً واردشده و Ruleهای تأییدشده را محاسبه می‌کند و هیچ نرخ، کرایه، بیمه یا ارز را حدس نمی‌زند.'})
    if data.persist:
        x=LandedCostCalculation(opportunity_id=opportunity_id,logistics_scenario_id=data.logistics_scenario_id,import_cost_rule_id=rule.id if rule else None,hs_code=hs,currency=data.currency,quantity=data.quantity,unit=data.unit,supplier_cost=data.supplier_cost,packaging_cost=data.packaging_cost,inland_cost=data.inland_cost,export_cost=data.export_cost,freight_cost=data.freight_cost,insurance_cost=data.insurance_cost,customs_value=result['customs_value'],import_taxes_and_fees=result['import_taxes_and_fees'],destination_handling=data.destination_handling,other_cost=data.other_cost,total_landed_cost=result['total_landed_cost'],landed_unit_cost=result['landed_unit_cost'],fx_rate=data.fx_rate,status='Calculated',assumptions=result['assumptions'])
        db.add(x); db.flush(); audit(db,admin,'landed_cost.calculated','LandedCostCalculation',x.id,{'opportunity_id':opportunity_id,'rule_id':rule.id if rule else None,'hs_code':hs}); db.commit(); result['calculation_id']=x.id
    return result

@router.post('/api/opportunities/{opportunity_id}/commercial-offers/{offer_id}/landed-cost')
def offer_landed_cost(opportunity_id:int, offer_id:int, data:LandedCostIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); op=db.get(Opportunity,opportunity_id); offer=db.get(CommercialOffer,offer_id)
    if not op or not offer or offer.opportunity_id!=opportunity_id: raise HTTPException(404,'فرصت یا پیشنهاد تجاری پیدا نشد.')
    # Offer values are the source of truth for the base commercial cost; request fields only override explicitly supplied logistics/import values.
    p=db.get(Product,op.product_id) if op.product_id else None; hs=data.hs_code; rule=None
    if data.import_cost_rule_id: rule=db.get(ImportCostRule,data.import_cost_rule_id)
    elif op.market_id and op.product_id:
        if not hs:
            pc=db.query(ProductCompliance).filter(ProductCompliance.product_id==op.product_id,ProductCompliance.market_id==op.market_id,ProductCompliance.status=='Verified').order_by(ProductCompliance.updated_at.desc()).first(); hs=pc.hs_code if pc else None
        if hs: rule=find_verified_rule(db,op.market_id,hs,p.name if p else None)
    cv=data.customs_value
    if rule:
        if rule.currency!=offer.currency and data.fx_rate is None: raise HTTPException(409,'برای اختلاف ارز Import Rule و Offer باید FX Rate صریح ارائه شود.')
        if cv is None: raise HTTPException(400,'customs_value الزامی است.')
        import_result=calculate_import_cost(rule,cv,offer.quantity,True)
    else:
        import_result=None
        if cv is not None: raise HTTPException(409,'customs_value بدون Rule تأییدشده قابل محاسبه نیست.')
    result=calculate_total_landed_cost(quantity=offer.quantity,unit=offer.unit,currency=offer.currency,supplier_cost=offer.supplier_unit_price*offer.quantity,packaging_cost=offer.packaging_cost,inland_cost=offer.inland_cost,export_cost=offer.export_cost,freight_cost=offer.freight_cost,insurance_cost=offer.insurance_cost,customs_value=cv,import_cost=import_result,destination_handling=0,other_cost=offer.other_cost,fx_rate=data.fx_rate,expected_currency=rule.currency if rule else None)
    offer.customs_cost=result['import_taxes_and_fees']; offer.landed_total=result['total_landed_cost']; offer.landed_unit_price=result['landed_unit_cost']
    offer.assumptions={**(offer.assumptions or {}),'landed_cost_calculation':result,'landed_cost_rule_id':rule.id if rule else None,'landed_cost_hs_code':hs}
    x=LandedCostCalculation(opportunity_id=opportunity_id,commercial_offer_id=offer.id,import_cost_rule_id=rule.id if rule else None,hs_code=hs,currency=offer.currency,quantity=offer.quantity,unit=offer.unit,supplier_cost=offer.supplier_unit_price*offer.quantity,packaging_cost=offer.packaging_cost,inland_cost=offer.inland_cost,export_cost=offer.export_cost,freight_cost=offer.freight_cost,insurance_cost=offer.insurance_cost,customs_value=result['customs_value'],import_taxes_and_fees=result['import_taxes_and_fees'],destination_handling=0,other_cost=offer.other_cost,total_landed_cost=result['total_landed_cost'],landed_unit_cost=result['landed_unit_cost'],fx_rate=data.fx_rate,status='Calculated',assumptions=result['assumptions'])
    db.add(x); db.flush(); audit(db,admin,'landed_cost.applied_to_offer','CommercialOffer',offer.id,{'calculation_id':x.id,'rule_id':rule.id if rule else None,'hs_code':hs}); db.commit(); db.refresh(offer)
    return {'status':'Applied','offer':serialize(offer),'landed_cost':result,'calculation_id':x.id}

@router.get('/api/opportunities/{opportunity_id}/landed-cost')
def opportunity_landed_cost_history(opportunity_id:int, request:Request, db:Session=Depends(get_db), limit:int=50):
    auth(request,db); op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت پیدا نشد.')
    rows=db.query(LandedCostCalculation).filter(LandedCostCalculation.opportunity_id==opportunity_id).order_by(LandedCostCalculation.created_at.desc()).limit(min(limit,200)).all()
    return [serialize(x) for x in rows]

# V23.5 Trade Route & Border Cost Intelligence
from ..services.trade_route import calculate_trade_route

@router.get('/api/opportunities/{opportunity_id}/trade-routes')
def list_trade_routes(opportunity_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    if not db.get(Opportunity,opportunity_id): raise HTTPException(404,'فرصت پیدا نشد.')
    rows=db.query(TradeRouteProfile).filter(TradeRouteProfile.opportunity_id==opportunity_id,TradeRouteProfile.is_active==True).order_by(TradeRouteProfile.created_at.desc()).all()
    return [{'route':serialize(r),'segments':[serialize(s) for s in db.query(TradeRouteSegment).filter(TradeRouteSegment.route_id==r.id).order_by(TradeRouteSegment.sequence).all()]} for r in rows]

@router.post('/api/opportunities/{opportunity_id}/trade-routes')
def create_trade_route(opportunity_id:int,data:TradeRouteProfileIn,request:Request,db:Session=Depends(get_db)):
    admin=auth(request,db)
    if not db.get(Opportunity,opportunity_id): raise HTTPException(404,'فرصت پیدا نشد.')
    row=TradeRouteProfile(opportunity_id=opportunity_id,**data.model_dump())
    db.add(row); db.flush(); audit(db,admin,'trade_route.created','TradeRouteProfile',row.id,{'origin':row.origin,'destination':row.destination}); db.commit(); db.refresh(row)
    return serialize(row)

@router.post('/api/opportunities/{opportunity_id}/trade-routes/{route_id}/segments')
def add_trade_route_segment(opportunity_id:int,route_id:int,data:TradeRouteSegmentIn,request:Request,db:Session=Depends(get_db)):
    admin=auth(request,db); route=db.get(TradeRouteProfile,route_id)
    if not route or route.opportunity_id!=opportunity_id: raise HTTPException(404,'مسیر تجاری پیدا نشد.')
    row=TradeRouteSegment(route_id=route_id,**data.model_dump()); db.add(row); db.flush(); audit(db,admin,'trade_route.segment_created','TradeRouteSegment',row.id,{'route_id':route_id,'sequence':row.sequence}); db.commit(); db.refresh(row)
    return serialize(row)

@router.post('/api/opportunities/{opportunity_id}/trade-routes/{route_id}/calculate')
def calculate_trade_route_endpoint(opportunity_id:int,route_id:int,data:TradeRouteCalculateIn,request:Request,db:Session=Depends(get_db)):
    admin=auth(request,db); route=db.get(TradeRouteProfile,route_id)
    if not route or route.opportunity_id!=opportunity_id: raise HTTPException(404,'مسیر تجاری پیدا نشد.')
    segments=db.query(TradeRouteSegment).filter(TradeRouteSegment.route_id==route_id).order_by(TradeRouteSegment.sequence).all()
    if not segments: raise HTTPException(400,'برای مسیر حداقل یک بخش مسیر لازم است.')
    
    if data.fx_rates:
        raise HTTPException(422,'ارسال نرخ ارز دستی مجاز نیست؛ نرخ‌ها باید از FXRate منبع‌دار خوانده شوند.')
    fx, fx_provenance = resolve_fx_map(db,[s.currency for s in segments],data.currency)
    try: result=calculate_trade_route([serialize(s) for s in segments],data.quantity,data.currency,fx)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    row=TradeRouteCalculation(route_id=route_id,opportunity_id=opportunity_id,quantity=data.quantity,currency=data.currency,freight_total=result['freight_total'],border_total=result['border_total'],transit_total=result['transit_total'],destination_handling=result['destination_handling_total'],other_cost=result['other_total'],total_route_cost=result['total_route_cost'],route_unit_cost=result['route_unit_cost'],distance_km=result['distance_km'],transit_days=result['transit_days'],status='Calculated',assumptions=result['assumptions'])
    db.add(row); db.flush(); audit(db,admin,'trade_route.calculated','TradeRouteCalculation',row.id,{'route_id':route_id,'opportunity_id':opportunity_id}); db.commit()
    result['calculation_id']=row.id; result['route_id']=route_id; result['fx_provenance']=fx_provenance; return result

@router.get('/api/opportunities/{opportunity_id}/trade-routes/{route_id}/calculations')
def trade_route_calculations(opportunity_id:int,route_id:int,request:Request,db:Session=Depends(get_db)):
    auth(request,db); route=db.get(TradeRouteProfile,route_id)
    if not route or route.opportunity_id!=opportunity_id: raise HTTPException(404,'مسیر تجاری پیدا نشد.')
    return [serialize(x) for x in db.query(TradeRouteCalculation).filter(TradeRouteCalculation.route_id==route_id).order_by(TradeRouteCalculation.created_at.desc()).limit(50).all()]

# V23.6 End-to-End Trade Cost & Route Optimizer
from ..services.trade_optimizer import optimize_trade_scenarios

@router.post('/api/opportunities/{opportunity_id}/trade-optimizer')
def trade_optimizer(opportunity_id:int,data:TradeOptimizationIn,request:Request,db:Session=Depends(get_db)):
    admin=auth(request,db); op=db.get(Opportunity,opportunity_id)
    if not op: raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    quotes=db.query(SupplierQuote).filter(SupplierQuote.opportunity_id==opportunity_id,SupplierQuote.id.in_(data.quote_ids)).all()
    routes=db.query(TradeRouteProfile).filter(TradeRouteProfile.opportunity_id==opportunity_id,TradeRouteProfile.id.in_(data.route_ids),TradeRouteProfile.is_active==True).all()
    if len(quotes)!=len(set(data.quote_ids)): raise HTTPException(404,'یک یا چند Supplier Quote پیدا نشد.')
    if len(routes)!=len(set(data.route_ids)): raise HTTPException(404,'یک یا چند Trade Route پیدا نشد.')
    if data.fx_rates:
        raise HTTPException(422,'ارسال نرخ ارز دستی مجاز نیست؛ نرخ‌ها باید از FXRate منبع‌دار خوانده شوند.')
    route_items=[]
    all_segment_currencies=[]
    for route in routes:
        segs=db.query(TradeRouteSegment).filter(TradeRouteSegment.route_id==route.id).order_by(TradeRouteSegment.sequence).all()
        if not segs: continue
        all_segment_currencies.extend([seg.currency for seg in segs])
    fx, fx_provenance = resolve_fx_map(db,[q.currency for q in quotes] + all_segment_currencies,data.target_currency)
    for route in routes:
        segs=db.query(TradeRouteSegment).filter(TradeRouteSegment.route_id==route.id).order_by(TradeRouteSegment.sequence).all()
        if not segs: continue
        route_fx, _route_fx_provenance = resolve_fx_map(db,[seg.currency for seg in segs],route.currency)
        try: calc=calculate_trade_route([serialize(s) for s in segs],data.quantity,route.currency,route_fx)
        except ValueError as exc: raise HTTPException(400,str(exc)) from exc
        route_items.append((route,calc))
    if not route_items: raise HTTPException(400,'هیچ مسیر دارای Segment معتبر نیست.')
    import_rules={}
    hs=None
    if op.product_id and op.market_id:
        pc=db.query(ProductCompliance).filter(ProductCompliance.product_id==op.product_id,ProductCompliance.market_id==op.market_id).order_by(ProductCompliance.updated_at.desc()).first()
        if pc and pc.status=='Verified':
            hs=pc.hs_code
            rule=find_verified_rule(db,op.market_id,hs)
            if rule:
                for rid in data.route_ids:
                    for q in data.quote_ids: import_rules[f'{q}:{rid}']=rule
    class RouteObj:
        def __init__(self,r,c): self.id=r.id; self.name=r.name; self.currency=r.currency; self.verification_status=r.verification_status; self.calculation=c
    route_objs=[RouteObj(r,c) for r,c in route_items]
    try: result=optimize_trade_scenarios(quotes=quotes,routes=route_objs,quantity=data.quantity,target_currency=data.target_currency,fx_rates=fx,import_rules=import_rules,customs_values=data.customs_values,limit=data.limit)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    run=TradeOptimizationRun(opportunity_id=opportunity_id,quantity=data.quantity,target_currency=data.target_currency,status='Calculated',scenario_count=result['scenario_count'],assumptions={'quote_ids':data.quote_ids,'route_ids':data.route_ids,'hs_code':hs,'explicit_fx_required':True},created_by=admin.id)
    db.add(run); db.flush()
    for rank,item in enumerate(result['scenarios'],1):
        row=TradeOptimizationResult(run_id=run.id,opportunity_id=opportunity_id,supplier_quote_id=item['supplier_quote_id'],route_id=item['route_id'],target_currency=item['target_currency'],quantity=item['quantity'],supplier_goods_total=item['supplier_goods_total'],supplier_other_cost=item['supplier_other_cost'],route_cost=item['route_cost'],import_taxes_and_fees=item['import_taxes_and_fees'],total_trade_cost=item['total_trade_cost'],trade_unit_cost=item['trade_unit_cost'],route_distance_km=item['route_distance_km'],route_transit_days=item['route_transit_days'],rank=rank,assumptions=item['assumptions'])
        db.add(row)
    audit(db,admin,'trade_optimizer.calculated','TradeOptimizationRun',run.id,{'scenario_count':result['scenario_count'],'hs_code':hs}); db.commit()
    result['run_id']=run.id; result['hs_code']=hs; result['fx_provenance']=fx_provenance; return result

@router.get('/api/opportunities/{opportunity_id}/trade-optimizer/runs')
def trade_optimizer_runs(opportunity_id:int,request:Request,db:Session=Depends(get_db),limit:int=20):
    auth(request,db)
    if not db.get(Opportunity,opportunity_id): raise HTTPException(404,'فرصت تجاری پیدا نشد.')
    rows=db.query(TradeOptimizationRun).filter(TradeOptimizationRun.opportunity_id==opportunity_id).order_by(TradeOptimizationRun.created_at.desc()).limit(min(limit,100)).all()
    return [serialize(x) for x in rows]

@router.get('/api/opportunities/{opportunity_id}/trade-optimizer/runs/{run_id}')
def trade_optimizer_run(opportunity_id:int,run_id:int,request:Request,db:Session=Depends(get_db)):
    auth(request,db); run=db.get(TradeOptimizationRun,run_id)
    if not run or run.opportunity_id!=opportunity_id: raise HTTPException(404,'اجرای Optimizer پیدا نشد.')
    rows=db.query(TradeOptimizationResult).filter(TradeOptimizationResult.run_id==run_id).order_by(TradeOptimizationResult.rank.asc()).all()
    return {'run':serialize(run),'results':[serialize(x) for x in rows]}

@router.post('/api/opportunities/{opportunity_id}/trade-optimizer/apply')
def trade_optimizer_apply(opportunity_id:int,data:TradeOptimizationApplyIn,request:Request,db:Session=Depends(get_db)):
    admin=auth(request,db); result=db.query(TradeOptimizationResult).filter(TradeOptimizationResult.id==data.result_id,TradeOptimizationResult.opportunity_id==opportunity_id).first()
    if not result: raise HTTPException(404,'نتیجه Optimizer پیدا نشد.')
    run=db.query(TradeOptimizationRun).filter(TradeOptimizationRun.id==result.run_id,TradeOptimizationRun.opportunity_id==opportunity_id).first()
    if not run: raise HTTPException(404,'Run پیدا نشد.')
    if not result: raise HTTPException(404,'نتیجه Optimizer پیدا نشد.')
    quote=db.get(SupplierQuote,result.supplier_quote_id)
    if not quote: raise HTTPException(404,'Supplier Quote پیدا نشد.')
    unit_supplier=result.supplier_goods_total/result.quantity if result.quantity else 0
    unit_route=result.route_cost/result.quantity if result.quantity else 0
    unit_import=result.import_taxes_and_fees/result.quantity if result.quantity else 0
    offer_data=CommercialOfferIn(supplier_quote_id=quote.id,currency=result.target_currency,exchange_rate=1,quantity=result.quantity,unit=quote.unit,supplier_unit_price=unit_supplier,freight_cost=unit_route*result.quantity,customs_cost=unit_import*result.quantity,other_cost=result.supplier_other_cost,target_margin_percent=data.target_margin_percent,commission_percent=data.commission_percent,commission_fixed=data.commission_fixed,status=data.status,notes=data.notes,assumptions={'trade_optimizer_run_id':run.id,'trade_optimizer_result_id':result.id,'route_id':result.route_id,'double_counting_protection':'supplier_freight_excluded_when_route_selected'},incoterm='LANDED')
    calc=_build_offer(offer_data,db); payload=offer_data.model_dump(); payload.update(calc); payload.pop('commission_amount',None); payload.pop('base_cost',None); payload.pop('fob_cost_before_margin',None)
    offer=CommercialOffer(opportunity_id=opportunity_id,created_by=admin.id,**payload); db.add(offer); db.flush(); audit(db,admin,'trade_optimizer.applied_to_offer','CommercialOffer',offer.id,{'run_id':run.id,'result_id':result.id,'route_id':result.route_id,'quote_id':quote.id}); db.commit(); db.refresh(offer)
    return {'status':'Applied','offer':serialize(offer),'optimization_result':serialize(result),'calculation':calc}
