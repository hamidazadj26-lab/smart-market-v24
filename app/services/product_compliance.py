from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models import ProductCompliance, ComplianceRequirement, TradeRule, Product, Market

STATUSES={'Verified','Partially Verified','Unverified','Rejected','Expired'}
REQ_TYPES={'license','certificate','standard','labeling','packaging','customs_document','testing','restriction','other'}

def _now(): return datetime.now(timezone.utc)

def serialize_profile(x):
    return {c.name:getattr(x,c.name) for c in x.__table__.columns}

def serialize_requirement(x):
    return serialize_profile(x)

def compliance_gate(db:Session, product:Product, market:Market, hs_code=None):
    q=db.query(ProductCompliance).filter(ProductCompliance.product_id==product.id,ProductCompliance.market_id==market.id)
    if hs_code: q=q.filter(ProductCompliance.hs_code==hs_code)
    profiles=q.order_by(ProductCompliance.updated_at.desc()).all()
    if not profiles:
        return {'status':'Blocked','reason':'No verified HS classification is registered for this product/market.','product_id':product.id,'market_id':market.id,'hs_code':hs_code,'profiles':[],'requirements':[],'blockers':['hs_classification']}
    profile=next((p for p in profiles if p.status=='Verified'),profiles[0])
    reqs=db.query(ComplianceRequirement).filter(ComplianceRequirement.product_compliance_id==profile.id).all()
    if not reqs:
        rules=db.query(TradeRule).filter(TradeRule.market_id==market.id,TradeRule.hs_code==profile.hs_code).all()
        reqs=[]
        for r in rules:
            reqs.append({'id':None,'trade_rule_id':r.id,'requirement_type':r.rule_type,'title':r.title,'mandatory':r.mandatory,'status':r.status,'documents':r.documents or [],'evidence':{},'source_url':r.source_url,'source_title':r.source_title,'notes':r.notes})
    blockers=[]
    for r in reqs:
        status=r.status if isinstance(r,dict) else r.status
        mandatory=r.mandatory if isinstance(r,dict) else r.mandatory
        if mandatory and status!='Verified': blockers.append(r['title'] if isinstance(r,dict) else r.title)
    result='Ready' if profile.status=='Verified' and not blockers else 'Needs Verification'
    return {'status':result,'product_id':product.id,'market_id':market.id,'product':product.name,'market':market.name,'hs_code':profile.hs_code,'hs_description':profile.hs_description,'classification_status':profile.status,'classification_confidence':profile.confidence,'mandatory_requirements':sum(1 for r in reqs if (r['mandatory'] if isinstance(r,dict) else r.mandatory)),'verified_requirements':sum(1 for r in reqs if (r['status'] if isinstance(r,dict) else r.status)=='Verified'),'blocker_count':len(blockers),'blockers':blockers,'profiles':[serialize_profile(x) for x in profiles],'requirements':[serialize_requirement(x) if not isinstance(x,dict) else x for x in reqs]}
