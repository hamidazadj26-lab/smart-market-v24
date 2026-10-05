"""Market and trade-rule API routes."""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import *
from ..schemas import *
from ..security.auth import *
from ..services.rbac import audit, require_permission
from ..services.request_guard import auth, serialize
from ..services.multi_market import get_or_create_market, serialize_market, DEFAULT_WEIGHTS
from ..services.trade_rules import serialize_country, serialize_rule, trade_readiness, RULE_TYPES, STATUSES

router = APIRouter(tags=["markets", "trade-rules"])

# V23.0 Multi-Market & Multi-Country Intelligence
@router.get('/api/markets')
def markets_list(request:Request, db:Session=Depends(get_db), active_only:bool=True):
    auth(request,db)
    q=db.query(Market)
    if active_only: q=q.filter(Market.active==True)
    return [serialize_market(x) for x in q.order_by(Market.name).all()]

@router.post('/api/markets')
def market_create(data:MarketProfileIn, request:Request, db:Session=Depends(get_db)):
    admin=auth(request,db); require_permission(request,db,'user.manage')
    if db.query(Market).filter(Market.name==data.name).first(): raise HTTPException(409,'بازار با این نام قبلاً ثبت شده است.')
    weights=data.scoring_weights or DEFAULT_WEIGHTS
    if abs(sum(float(v) for v in weights.values())-100)>0.01: raise HTTPException(400,'مجموع وزن‌های امتیازدهی باید 100 باشد.')
    m=Market(**data.model_dump()); m.scoring_weights=weights
    db.add(m); db.add(AuditLog(admin_id=admin.id,action='market_profile_created',entity_type='market',entity_id=0,details={'name':data.name,'source_country':data.source_country,'target_country':data.target_country})); db.commit(); db.refresh(m)
    return serialize_market(m)

@router.get('/api/markets/{market_id}')
def market_get(market_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db); m=db.get(Market,market_id)
    if not m: raise HTTPException(404,'بازار پیدا نشد.')
    return serialize_market(m)

@router.get('/api/markets/{market_id}/stats')
def market_stats(market_id:int, request:Request, db:Session=Depends(get_db)):
    auth(request,db); m=db.get(Market,market_id)
    if not m: raise HTTPException(404,'بازار پیدا نشد.')
    total=db.query(Opportunity).filter(Opportunity.market_id==market_id,Opportunity.is_archived==False).count()
    customers=db.query(Customer).filter(Customer.country==m.target_country,Customer.is_archived==False).count()
    suppliers=db.query(Manufacturer).filter(Manufacturer.country==m.source_country,Manufacturer.is_archived==False).count()
    demands=db.query(Demand).filter(Demand.country==m.target_country,Demand.is_archived==False).count()
    return {'market':serialize_market(m),'stats':{'opportunities':total,'suppliers':suppliers,'customers':customers,'demands':demands}}

@router.get('/api/country-profiles')
def country_profiles(request:Request, db:Session=Depends(get_db)):
    auth(request,db)
    return [serialize_country(x) for x in db.query(CountryProfile).order_by(CountryProfile.country_name).all()]

@router.post('/api/country-profiles')
def country_profile_create(data:CountryProfileIn, request:Request, db:Session=Depends(get_db)):
    admin=require_permission(request,db,'market_rules.write')
    code=data.country_code.strip().upper()
    if db.query(CountryProfile).filter(CountryProfile.country_code==code).first(): raise HTTPException(409,'پروفایل این کشور قبلاً ثبت شده است.')
    payload=data.model_dump(); payload['country_code']=code
    x=CountryProfile(**payload); db.add(x); db.flush(); audit(db,admin,'country_profile.created','CountryProfile',x.id,{'country_code':code}); db.commit(); db.refresh(x)
    return serialize_country(x)

@router.get('/api/trade-rules/types')
def trade_rule_types(request:Request, db:Session=Depends(get_db)):
    auth(request,db); return {'rule_types':sorted(RULE_TYPES),'statuses':sorted(STATUSES)}

@router.get('/api/trade-rules')
def trade_rules(request:Request, db:Session=Depends(get_db), market_id:int|None=None, product_scope:str|None=None, hs_code:str|None=None, current_only:bool=True):
    auth(request,db); q=db.query(TradeRule)
    if market_id is not None: q=q.filter(TradeRule.market_id==market_id)
    if product_scope: q=q.filter(or_(TradeRule.product_scope==None, TradeRule.product_scope.ilike(f'%{product_scope}%')))
    if hs_code: q=q.filter(or_(TradeRule.hs_code==None, TradeRule.hs_code==hs_code))
    rules=q.order_by(TradeRule.mandatory.desc(),TradeRule.rule_type,TradeRule.title).all()
    from ..services.trade_rules import rule_is_current
    return [serialize_rule(r) for r in rules if (not current_only or rule_is_current(r))]

@router.post('/api/trade-rules')
def trade_rule_create(data:TradeRuleIn, request:Request, db:Session=Depends(get_db)):
    admin=require_permission(request,db,'market_rules.write')
    if not db.get(Market,data.market_id): raise HTTPException(404,'بازار پیدا نشد.')
    if data.country_profile_id and not db.get(CountryProfile,data.country_profile_id): raise HTTPException(404,'پروفایل کشور پیدا نشد.')
    if data.rule_type not in RULE_TYPES: raise HTTPException(400,'نوع Rule نامعتبر است.')
    if data.status not in STATUSES: raise HTTPException(400,'وضعیت Rule نامعتبر است.')
    x=TradeRule(**data.model_dump()); db.add(x); db.flush(); audit(db,admin,'trade_rule.created','TradeRule',x.id,{'market_id':x.market_id,'rule_type':x.rule_type,'hs_code':x.hs_code}); db.commit(); db.refresh(x)
    return serialize_rule(x)

@router.patch('/api/trade-rules/{rule_id}')
def trade_rule_update(rule_id:int, data:TradeRuleIn, request:Request, db:Session=Depends(get_db)):
    admin=require_permission(request,db,'market_rules.write'); x=db.get(TradeRule,rule_id)
    if not x: raise HTTPException(404,'Rule پیدا نشد.')
    if data.rule_type not in RULE_TYPES or data.status not in STATUSES: raise HTTPException(400,'Rule type/status نامعتبر است.')
    for k,v in data.model_dump().items(): setattr(x,k,v)
    audit(db,admin,'trade_rule.updated','TradeRule',x.id,{'market_id':x.market_id,'status':x.status}); db.commit(); db.refresh(x); return serialize_rule(x)

@router.get('/api/markets/{market_id}/trade-readiness')
def market_trade_readiness(market_id:int, request:Request, db:Session=Depends(get_db), product_scope:str|None=None, hs_code:str|None=None):
    auth(request,db); m=db.get(Market,market_id)
    if not m: raise HTTPException(404,'بازار پیدا نشد.')
    return trade_readiness(db,m,product_scope,hs_code)

