from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models import CountryProfile, TradeRule, Market

RULE_TYPES={'import_license','hs_classification','customs_document','product_standard','labeling','packaging','payment','sanctions_restriction','tax_duty','logistics','border','other'}
STATUSES={'Verified','Partially Verified','Unverified','Expired'}

def _now(): return datetime.now(timezone.utc)

def serialize_country(c):
    return {'id':c.id,'country_code':c.country_code,'country_name':c.country_name,'currencies':c.currencies or [],'languages':c.languages or [],'payment_methods':c.payment_methods or [],'customs_notes':c.customs_notes or {},'logistics_nodes':c.logistics_nodes or [],'source_url':c.source_url,'source_title':c.source_title,'retrieved_at':c.retrieved_at,'verification_status':c.verification_status}

def serialize_rule(r):
    return {'id':r.id,'market_id':r.market_id,'country_profile_id':r.country_profile_id,'rule_type':r.rule_type,'title':r.title,'hs_code':r.hs_code,'product_scope':r.product_scope,'mandatory':r.mandatory,'status':r.status,'requirement':r.requirement,'documents':r.documents or [],'authority':r.authority,'source_url':r.source_url,'source_title':r.source_title,'published_at':r.published_at,'effective_from':r.effective_from,'effective_to':r.effective_to,'retrieved_at':r.retrieved_at,'notes':r.notes}

def rule_is_current(r, now=None):
    now=now or _now()
    if r.status=='Expired': return False
    if r.effective_from and r.effective_from>now: return False
    if r.effective_to and r.effective_to<now: return False
    return True

def trade_readiness(db:Session, market:Market, product_scope=None, hs_code=None):
    q=db.query(TradeRule).filter(TradeRule.market_id==market.id)
    rules=[r for r in q.all() if rule_is_current(r)]
    if product_scope:
        rules=[r for r in rules if not r.product_scope or r.product_scope.lower() in product_scope.lower() or product_scope.lower() in r.product_scope.lower()]
    if hs_code:
        rules=[r for r in rules if not r.hs_code or r.hs_code==hs_code]
    mandatory=[r for r in rules if r.mandatory]
    blockers=[r for r in mandatory if r.status!='Verified']
    verified=sum(1 for r in rules if r.status=='Verified')
    score=100 if not mandatory else round(100*verified/max(len(rules),1),1)
    return {'market':{'id':market.id,'name':market.name,'source_country':market.source_country,'target_country':market.target_country},'product_scope':product_scope,'hs_code':hs_code,'rule_count':len(rules),'mandatory_count':len(mandatory),'verified_count':verified,'blocker_count':len(blockers),'readiness_score':score,'status':'Ready' if not blockers else 'Needs Verification','blocking_rules':[serialize_rule(r) for r in blockers],'rules':[serialize_rule(r) for r in rules]}
