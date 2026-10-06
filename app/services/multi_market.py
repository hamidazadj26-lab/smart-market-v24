from sqlalchemy.orm import Session
from ..models.models import Market

DEFAULT_WEIGHTS={"product_fit":30,"capacity":15,"demand":25,"trust":20,"location":10}
DEFAULTS={
 "Iran → Afghanistan":{"source_country":"Iran","target_country":"Afghanistan","currency":"USD","languages":["fa","ps","en"],"incoterms":["EXW","FCA","FOB","CFR","CIF","DAP"],"transport_modes":["road","rail","multimodal"],"commercial_rules":{"customs_required":True}},
 "Iran → Oman":{"source_country":"Iran","target_country":"Oman","currency":"USD","languages":["fa","ar","en"],"incoterms":["EXW","FCA","FOB","CFR","CIF","DAP","DDP"],"transport_modes":["sea","road","multimodal"],"commercial_rules":{"customs_required":True}},
 "Iran → Iraq":{"source_country":"Iran","target_country":"Iraq","currency":"USD","languages":["fa","ar","en"],"incoterms":["EXW","FCA","FOB","CFR","CIF","DAP"],"transport_modes":["road","multimodal"],"commercial_rules":{"customs_required":True}},
 "China → Afghanistan":{"source_country":"China","target_country":"Afghanistan","currency":"USD","languages":["en","ps","zh"],"incoterms":["FOB","CFR","CIF","DAP"],"transport_modes":["sea","rail","road","multimodal"],"commercial_rules":{"customs_required":True}},
}

def market_name(source,target): return f"{source.strip()} → {target.strip()}"

def parse_market_name(name: str | None):
    if not name or '→' not in name:
        return None
    source, target = (x.strip() for x in name.split('→', 1))
    if not source or not target:
        return None
    return source, target

def resolve_market(db: Session, name: str | None, *, allow_create: bool = True):
    """Resolve an explicit market; no business logic should assume a country pair."""
    parsed = parse_market_name(name)
    if not parsed:
        raise ValueError('market must be provided as Source → Target')
    source, target = parsed
    return get_or_create_market(db, source, target, market_name(source, target)) if allow_create else db.query(Market).filter(Market.name == market_name(source, target)).first()

def get_or_create_market(db:Session, source_country:str, target_country:str, name:str|None=None):
    name=name or market_name(source_country,target_country)
    m=db.query(Market).filter(Market.name==name).first()
    if not m:
        d=DEFAULTS.get(name,{})
        m=Market(name=name,source_country=source_country,target_country=target_country,default_currency=d.get("currency","USD"),languages=d.get("languages",["en"]),incoterms=d.get("incoterms",["EXW","FOB","CIF"]),transport_modes=d.get("transport_modes",["road"]),scoring_weights=d.get("weights",DEFAULT_WEIGHTS),commercial_rules=d.get("commercial_rules",{}),active=True)
        db.add(m); db.commit(); db.refresh(m)
    return m

def serialize_market(m):
    return {"id":m.id,"name":m.name,"source_country":m.source_country,"target_country":m.target_country,"active":m.active,"default_currency":m.default_currency,"languages":m.languages or [],"incoterms":m.incoterms or [],"transport_modes":m.transport_modes or [],"scoring_weights":m.scoring_weights or DEFAULT_WEIGHTS,"commercial_rules":m.commercial_rules or {}}
