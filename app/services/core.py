import math
from sqlalchemy.orm import Session
from ..models import Product, Manufacturer, Customer, Demand, Opportunity, Market, Supplier, Buyer
from ..matching.scoring import calculate as calculate_match_score
from ..matching.engine import match as match_entities
from ..opportunity.engine import evaluate_opportunity
from .closed_loop import summarize_actor
from .source_evidence import evidence_chain

ALIASES={'رزین اپوکسی':'epoxy resin','epoxy resin':'epoxy resin','چسب بتن':'concrete adhesive','مواد شوینده':'detergent','هیومیک اسید':'humic acid','سیمان':'cement'}

def normalize_product(name:str)->str:
    n=' '.join(name.lower().strip().split())
    return ALIASES.get(n,n)

def get_or_create_product(db:Session,name:str):
    norm=normalize_product(name); p=db.query(Product).filter(Product.normalized_name==norm).first()
    if not p:
        p=Product(name=name.strip(),normalized_name=norm); db.add(p); db.commit(); db.refresh(p)
    return p

def haversine(a,b,c,d):
    if None in (a,b,c,d): return None
    r=6371.0088; p1,p2=math.radians(a),math.radians(c); dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(x))

def score(man, cus, dem, weights=None):
    """Backward-compatible tuple API for existing callers/tests."""
    s=calculate_match_score(man,cus,dem,weights)
    return s.total,s.product_fit,s.capacity,s.demand,s.trust,s.location,s.distance_km,s.priority,s.reasons

def _canonical_key(*parts):
    return '|'.join(str(x or '').strip().lower() for x in parts)

def _ensure_canonical_actors(db: Session, manufacturer: Manufacturer, customer: Customer):
    supplier_key=_canonical_key(manufacturer.name, manufacturer.country, manufacturer.city, manufacturer.phone, manufacturer.website)
    supplier=db.query(Supplier).filter(Supplier.canonical_key==supplier_key).first()
    if not supplier:
        # Canonical keys may legitimately change when a phone/site is discovered.
        # Resolve first by the more stable name + geography before creating a duplicate.
        supplier=db.query(Supplier).filter(
            Supplier.canonical_name==manufacturer.name,
            Supplier.country==manufacturer.country,
            Supplier.city==manufacturer.city,
            Supplier.is_archived==False,
        ).first()
    if not supplier:
        supplier=Supplier(canonical_name=manufacturer.name, country=manufacturer.country, city=manufacturer.city, address=manufacturer.address, phone=manufacturer.phone, website=manufacturer.website, verification_status=manufacturer.verification_status, confidence=manufacturer.confidence, canonical_key=supplier_key)
        db.add(supplier); db.flush()
    else:
        # Keep the canonical actor synchronized with newer source-backed identity data.
        for field in ('canonical_name','country','city','address','phone','website'):
            value=getattr(manufacturer,field,None)
            if value not in (None,''):
                setattr(supplier,field,value)
        if manufacturer.verification_status == 'Verified' or supplier.verification_status == 'Unverified':
            supplier.verification_status=manufacturer.verification_status
        supplier.confidence=max(float(supplier.confidence or 0), float(manufacturer.confidence or 0))
        supplier.canonical_key=supplier_key
    buyer_key=_canonical_key(customer.name, customer.country, customer.city, customer.phone, customer.website)
    buyer=db.query(Buyer).filter(Buyer.canonical_key==buyer_key).first()
    if not buyer:
        buyer=db.query(Buyer).filter(
            Buyer.canonical_name==customer.name,
            Buyer.country==customer.country,
            Buyer.city==customer.city,
            Buyer.is_archived==False,
        ).first()
    if not buyer:
        buyer=Buyer(canonical_name=customer.name, country=customer.country, city=customer.city, address=customer.address, phone=customer.phone, website=customer.website, verification_status='Potential' if customer.verification_status=='Unverified' else customer.verification_status, confidence=customer.confidence, canonical_key=buyer_key)
        db.add(buyer); db.flush()
    else:
        for field in ('canonical_name','country','city','address','phone','website'):
            value=getattr(customer,field,None)
            if value not in (None,''):
                setattr(buyer,field,value)
        incoming_status='Potential' if customer.verification_status=='Unverified' else customer.verification_status
        if incoming_status == 'Verified' or buyer.verification_status == 'Potential':
            buyer.verification_status=incoming_status
        buyer.confidence=max(float(buyer.confidence or 0), float(customer.confidence or 0))
        buyer.canonical_key=buyer_key
    return supplier, buyer

def rebuild_opportunities(db:Session, product_id=None):
    q=db.query(Demand).filter(Demand.is_archived==False)
    if product_id: q=q.filter(Demand.product_id==product_id)
    demands=q.all(); created=[]
    for d in demands:
        mans=db.query(Manufacturer).filter(Manufacturer.product_id==d.product_id,Manufacturer.is_archived==False).all()
        cus=db.query(Customer).filter(Customer.product_id==d.product_id,Customer.country==d.country,Customer.is_archived==False).all()
        for m in mans:
            for c in cus:
                exists=db.query(Opportunity).filter(Opportunity.manufacturer_id==m.id,Opportunity.customer_id==c.id,Opportunity.demand_id==d.id,Opportunity.is_archived==False).first()
                if exists: continue
                market=db.query(Market).filter(Market.source_country==m.country,Market.target_country==c.country,Market.active==True).first()
                weights=(market.scoring_weights if market else None)
                # Initial eligibility is checked before actor evidence; the final score is recalculated below with all observed dimensions.
                buyer_feedback = summarize_actor(db, customer_id=c.id)
                supplier_feedback = summarize_actor(db, manufacturer_id=m.id)
                buyer_rel = buyer_feedback['reliability_score'] * 100 if buyer_feedback['feedback_count'] >= 3 and buyer_feedback['reliability_score'] is not None else None
                supplier_rel = supplier_feedback['reliability_score'] * 100 if supplier_feedback['feedback_count'] >= 3 and supplier_feedback['reliability_score'] is not None else None
                chains = [evidence_chain(db, et, eid) for et, eid in [('manufacturer', m.id), ('customer', c.id), ('demand', d.id)]]
                evidence_values = [x['score'] * 100 for x in chains if x.get('evidence_count')]
                freshness_values = [x['freshness'] * 100 for chain in chains for x in chain.get('evidence', []) if x.get('freshness') is not None]
                actor_evidence = {
                    'buyer_reliability': buyer_rel,
                    'supplier_reliability': supplier_rel,
                    'evidence': sum(evidence_values) / len(evidence_values) if evidence_values else None,
                    'freshness': sum(freshness_values) / len(freshness_values) if freshness_values else None,
                    'logistics': 100.0 if dist is not None and dist < 500 else 80.0 if dist is not None and dist < 1000 else 60.0 if dist is not None else None,
                }
                result=match_entities(m,c,d,weights,actor_evidence=actor_evidence)
                if result is None:
                    continue
                s=result['score']
                total,pf,cap,ds,trust,ls,dist,match_priority,match_reasons=(s.total,s.product_fit,s.capacity,s.demand,s.trust,s.location,s.distance_km,s.priority,s.reasons)
                intelligence=evaluate_opportunity(m,c,d,market=market,match=s,weights=None,actor_evidence=actor_evidence)
                supplier, buyer = _ensure_canonical_actors(db, m, c)
                o=Opportunity(manufacturer_id=m.id,customer_id=c.id,supplier_id=supplier.id,buyer_id=buyer.id,demand_id=d.id,product_id=d.product_id,market_id=(market.id if market else None),score=round(intelligence['score'].total,2),product_fit=pf,capacity_score=cap,demand_score=ds,trust_score=trust,location_score=ls,price_score=s.price,logistics_score=s.logistics,evidence_score=s.evidence,freshness_score=s.freshness,buyer_reliability_score=s.buyer_reliability,supplier_reliability_score=s.supplier_reliability,score_breakdown=s.dimension_evidence,distance_km=dist,priority=intelligence['score'].priority,verification_status='Unverified',next_action='ابتدا ظرفیت تولیدکننده و فعال بودن تقاضای خریدار را تأیید کنید.',route={'score_reasons':match_reasons,'opportunity_intelligence':intelligence['explanation'],'actor_evidence':actor_evidence,'match_score':round(total,2),'match_priority':match_priority})
                db.add(o); created.append(o)
    db.commit(); return created
