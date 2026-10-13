from datetime import datetime, timezone, timedelta
from app.services.search_cache import cache_key, put_cached, get_cached
from app.services.job_queue import create_job, claim_next, consume_request, finish_job, can_access_job
from app.models import SearchCache, DiscoveryJob
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base

def db_session():
    engine=create_engine('sqlite:///:memory:', connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()

def test_cache_key_is_stable_and_parameter_sensitive():
    a=cache_key('web','steel pump',{'market':'AFG'})
    b=cache_key('web','steel pump',{'market':'AFG'})
    c=cache_key('web','steel pump',{'market':'IRQ'})
    assert a==b and a!=c and len(a)==64

def test_cache_put_hit_and_expiry():
    db=db_session()
    row=put_cached(db,'web','q',{'items':[1]},ttl_seconds=60,params={'x':1}); db.commit()
    hit=get_cached(db,'web','q',{'x':1})
    assert hit and hit.hit_count==1
    row.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1); db.commit()
    assert get_cached(db,'web','q',{'x':1}) is None

def test_durable_job_queue_budget_and_completion():
    db=db_session()
    job=create_job(db,'external_discovery',{'product':'pump'},max_requests=2,max_retries=1); db.commit()
    claimed=claim_next(db); assert claimed.id==job.id and claimed.status=='running'
    consume_request(claimed); consume_request(claimed)
    try:
        consume_request(claimed)
        assert False
    except RuntimeError:
        pass
    finish_job(db,claimed,'completed',{'count':2}); db.commit()
    assert claimed.status=='completed' and claimed.requests_used==2


def test_discovery_job_access_is_scoped_to_creator_or_super_admin():
    from types import SimpleNamespace
    db=db_session()
    job=create_job(db,'external_discovery',{'product':'pump'},created_by=7); db.commit()
    assert can_access_job(job, SimpleNamespace(id=7, role='Sales'))
    assert not can_access_job(job, SimpleNamespace(id=8, role='Sales'))
    assert can_access_job(job, SimpleNamespace(id=8, role='Super Admin'))
    legacy=create_job(db,'external_discovery',{},created_by=None); db.commit()
    assert not can_access_job(legacy, SimpleNamespace(id=7, role='Sales'))
    assert can_access_job(legacy, SimpleNamespace(id=7, role='Super Admin'))


def test_stale_running_job_is_requeued_then_failed_after_retry_limit():
    from app.services.job_queue import recover_stale_jobs
    db = db_session()
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    job = create_job(db, 'external_discovery', {}, max_retries=1)
    job.status = 'running'
    job.started_at = old
    job.heartbeat_at = old
    db.commit()

    result = recover_stale_jobs(db, stale_after_seconds=3600)
    db.commit()
    assert result == {'requeued': 1, 'failed': 0}
    db.refresh(job)
    assert job.status == 'queued' and job.retry_count == 1
    assert job.started_at is None and job.heartbeat_at is None

    job.status = 'running'
    job.started_at = old
    job.heartbeat_at = old
    db.commit()
    result = recover_stale_jobs(db, stale_after_seconds=3600)
    db.commit()
    assert result == {'requeued': 0, 'failed': 1}
    db.refresh(job)
    assert job.status == 'failed' and job.finished_at is not None


def test_recent_heartbeat_prevents_stale_job_recovery():
    from app.services.job_queue import recover_stale_jobs
    db = db_session()
    job = create_job(db, 'external_discovery', {}, max_retries=2)
    job.status = 'running'
    job.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
    job.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    db.commit()
    result = recover_stale_jobs(db, stale_after_seconds=3600)
    db.commit()
    db.refresh(job)
    assert result == {'requeued': 0, 'failed': 0}
    assert job.status == 'running'


def test_expired_worker_lease_cannot_heartbeat_or_finish_reclaimed_job():
    from app.services.job_queue import recover_stale_jobs, heartbeat_job
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import tempfile, os
    fd, db_path = tempfile.mkstemp(suffix='.sqlite3'); os.close(fd)
    engine = create_engine('sqlite:///' + db_path, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    owner = Session()
    stale_db = Session()
    try:
        job = create_job(owner, 'external_discovery', {}, max_retries=2)
        owner.commit()
        stale_worker = claim_next(stale_db)
        stale_token = stale_worker.lease_token
        stale_worker.heartbeat_at = datetime.now(timezone.utc) - timedelta(hours=2)
        stale_db.commit()

        recovered = recover_stale_jobs(owner, stale_after_seconds=3600)
        owner.commit()
        assert recovered == {'requeued': 1, 'failed': 0}
        from uuid import uuid4
        fresh_token = uuid4().hex
        owner.query(type(job)).filter(type(job).id == job.id).update({type(job).status: 'running', type(job).lease_token: fresh_token, type(job).heartbeat_at: datetime.now(timezone.utc)}, synchronize_session=False)
        owner.commit()
        owner.expire(job)
        fresh_worker = owner.get(type(job), job.id)
        assert fresh_worker.lease_token != stale_token

        # The old worker session cannot refresh or finish the new worker's lease.
        assert heartbeat_job(stale_db, stale_worker) is False
        try:
            finish_job(stale_db, stale_worker, 'completed', {'stale': True})
            assert False, 'stale lease should be rejected'
        except RuntimeError as exc:
            assert 'lease lost' in str(exc)
        stale_db.rollback()
        owner.refresh(fresh_worker)
        assert fresh_worker.status == 'running'
        assert fresh_worker.lease_token is not None
    finally:
        owner.close(); stale_db.close(); engine.dispose(); os.unlink(db_path)
