import re
from difflib import SequenceMatcher
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from ..models import Customer, Manufacturer, EntityIdentity, EntityLink


def normalize_text(value):
    if not value: return ''
    s=str(value).strip().lower().replace('ي','ی').replace('ى','ی').replace('ك','ک')
    s=re.sub(r'[\u064B-\u065F\u0670]', '', s)
    s=re.sub(r'[^\w\s]', ' ', s, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', s).strip()


def normalize_phone(value):
    if not value: return ''
    s=str(value).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789'))
    return re.sub(r'\D','',s)


def normalize_domain(value):
    if not value: return ''
    raw=str(value).strip().lower()
    if '://' not in raw: raw='https://'+raw
    try: return (urlparse(raw).hostname or '').lower().removeprefix('www.')
    except Exception: return ''


def entity_record(entity):
    return {
        'entity_type': 'customer' if isinstance(entity, Customer) else 'manufacturer',
        'entity_id': entity.id,
        'name': entity.name,
        'company': getattr(entity,'company',None),
        'phone': entity.phone,
        'website': entity.website,
        'domain': normalize_domain(entity.website),
        'country': entity.country,
        'city': entity.city,
        'address': entity.address,
        'normalized_name': normalize_text(entity.name),
    }


def score_pair(a,b):
    reasons=[]; score=0.0
    an=normalize_text(a.name); bn=normalize_text(b.name)
    if an and bn:
        ratio=SequenceMatcher(None,an,bn).ratio(); score += ratio*45
        if an==bn: reasons.append('exact_normalized_name')
    ap=normalize_phone(a.phone); bp=normalize_phone(b.phone)
    if ap and bp and ap==bp: score += 35; reasons.append('exact_phone')
    ad=normalize_domain(a.website); bd=normalize_domain(b.website)
    if ad and bd and ad==bd: score += 35; reasons.append('exact_domain')
    if a.country and b.country and normalize_text(a.country)==normalize_text(b.country): score += 5; reasons.append('same_country')
    if a.city and b.city and normalize_text(a.city)==normalize_text(b.city): score += 5; reasons.append('same_city')
    return min(100.0,score), reasons


def find_candidates(db: Session, entity_type, entity_id, limit=20):
    model=Customer if entity_type=='customer' else Manufacturer if entity_type=='manufacturer' else None
    if model is None: raise ValueError('invalid entity type')
    target=db.get(model, entity_id)
    if not target: return []
    rows=db.query(model).filter(model.id!=entity_id, model.is_archived==False).limit(500).all()
    out=[]
    for row in rows:
        score,reasons=score_pair(target,row)
        if score>=45:
            out.append({'entity':entity_record(row),'score':round(score,2),'reasons':reasons,'decision':'candidate'})
    return sorted(out,key=lambda x:x['score'],reverse=True)[:limit]


def strong_identity(db, entity_type, entity_id):
    candidates=find_candidates(db,entity_type,entity_id,limit=5)
    return [x for x in candidates if x['score']>=80 and x['reasons']]
