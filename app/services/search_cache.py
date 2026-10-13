import hashlib, json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from ..models import SearchCache


def cache_key(source: str, query: str, params: dict | None = None) -> str:
    payload=json.dumps({'source':source,'query':query,'params':params or {}},sort_keys=True,ensure_ascii=False,separators=(',',':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def get_cached(db: Session, source: str, query: str, params: dict | None = None):
    key=cache_key(source,query,params)
    row=db.query(SearchCache).filter(SearchCache.cache_key==key).first()
    if not row or row.expires_at <= datetime.now(timezone.utc):
        return None
    row.hit_count += 1
    row.last_hit_at=datetime.now(timezone.utc)
    db.flush()
    return row


def put_cached(db: Session, source: str, query: str, payload: dict, ttl_seconds: int=900, params: dict | None=None):
    key=cache_key(source,query,params)
    now=datetime.now(timezone.utc)
    row=db.query(SearchCache).filter(SearchCache.cache_key==key).first()
    if row is None:
        row=SearchCache(cache_key=key,source=source,query=query,parameters=params or {},payload=payload,expires_at=now+timedelta(seconds=max(1,ttl_seconds)),created_at=now,updated_at=now)
        db.add(row)
    else:
        row.payload=payload; row.parameters=params or {}; row.expires_at=now+timedelta(seconds=max(1,ttl_seconds)); row.updated_at=now
    db.flush(); return row
