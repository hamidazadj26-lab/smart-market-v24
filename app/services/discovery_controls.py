from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, update
from sqlalchemy.orm import Session
from ..models import DiscoveryUsage, DiscoveryJob, Source
from ..services.search_cache import get_cached, put_cached

class DiscoveryBudgetExceeded(RuntimeError): pass

def _window():
    now=datetime.now(timezone.utc)
    return now.replace(second=0,microsecond=0)

def _consume_scope(db: Session, scope_type:str, scope_key:str, limit:int):
    start=_window()
    row=(db.query(DiscoveryUsage)
         .filter_by(scope_type=scope_type,scope_key=scope_key,window_started_at=start)
         .with_for_update()
         .first())
    if row is None:
        # The unique window index is the final arbiter when concurrent callers
        # create the same scope. Savepoint keeps the surrounding transaction usable.
        from sqlalchemy.exc import IntegrityError
        try:
            with db.begin_nested():
                row=DiscoveryUsage(scope_type=scope_type,scope_key=scope_key,
                    window_started_at=start,request_limit=max(1,limit),requests_used=0)
                db.add(row); db.flush()
        except IntegrityError:
            row=(db.query(DiscoveryUsage)
                 .filter_by(scope_type=scope_type,scope_key=scope_key,window_started_at=start)
                 .with_for_update()
                 .first())
    if row is None:
        raise DiscoveryBudgetExceeded(f'{scope_type} usage counter unavailable')
    # Conditional UPDATE prevents two transactions from consuming the last slot.
    result=db.execute(
        update(DiscoveryUsage)
        .where(DiscoveryUsage.id==row.id,
               DiscoveryUsage.requests_used < DiscoveryUsage.request_limit)
        .values(requests_used=DiscoveryUsage.requests_used + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise DiscoveryBudgetExceeded(f'{scope_type} request budget exceeded')
    db.refresh(row)
    return row

def consume_request(db:Session, job:DiscoveryJob, *, source_key:str, user_id:int|None, settings):
    if job.requests_used >= job.request_budget:
        raise DiscoveryBudgetExceeded('job request budget exceeded')
    _consume_scope(db,'global','global',settings.discovery_global_requests_per_minute)
    _consume_scope(db,'source',source_key,settings.discovery_source_requests_per_minute)
    if user_id is not None:
        _consume_scope(db,'user',str(user_id),settings.discovery_user_requests_per_minute)
    job.requests_used += 1
    return job

def mark_source(db:Session, source_key:str, *, success:bool, error:str|None=None):
    row=db.query(Source).filter(Source.name==source_key).first()
    if row is None:
        row=Source(source_type='external_discovery',name=source_key,access_mode='public_web',capability='external_search',configured=True,availability_status='Unknown')
        db.add(row); db.flush()
    now=datetime.now(timezone.utc); row.last_checked_at=now
    if success:
        row.availability_status='Available'; row.last_success_at=now; row.last_error=None
    else:
        row.last_error=error
        text=(error or '').lower()
        if '429' in text or 'rate' in text: row.availability_status='Rate Limited'
        elif '403' in text or 'blocked' in text or 'access denied' in text: row.availability_status='Blocked'
        elif 'timeout' in text: row.availability_status='Temporarily Failed'
        else: row.availability_status='Temporarily Failed'
    return row

async def cached_external(db:Session, job:DiscoveryJob, *, source_key:str, query:str, params:dict, user_id:int|None, settings, fetcher):
    hit=get_cached(db,source_key,query,params)
    if hit is not None:
        return hit.payload, {'cache':'hit','requests_used':job.requests_used}
    consume_request(db,job,source_key=source_key,user_id=user_id,settings=settings)
    try:
        payload=await fetcher()
        if payload is None:
            raise RuntimeError('empty external response')
        put_cached(db,source_key,query,payload,ttl_seconds=settings.discovery_cache_ttl_seconds,params=params)
        mark_source(db,source_key,success=True)
        return payload, {'cache':'miss','requests_used':job.requests_used}
    except Exception as exc:
        mark_source(db,source_key,success=False,error=str(exc))
        raise
