from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import update
from sqlalchemy.orm import Session
from ..models import DiscoveryJob

TERMINAL = {"completed", "failed", "cancelled"}
DEFAULT_STALE_AFTER_SECONDS = 3600

def can_access_job(job: DiscoveryJob, admin) -> bool:
    """Limit job visibility/control to its creator or a Super Admin."""
    if getattr(admin, "role", None) == "Super Admin":
        return True
    return job.created_by is not None and job.created_by == getattr(admin, "id", None)

def create_job(db: Session, job_type: str, payload: dict, max_requests: int = 50, max_retries: int = 3, created_by: int | None = None):
    job = DiscoveryJob(job_type=job_type, status="queued", payload=payload, request_budget=max(1, max_requests), requests_used=0, max_retries=max(0, max_retries), retry_count=0, created_by=created_by)
    db.add(job)
    db.flush()
    return job

def heartbeat_job(db: Session, job: DiscoveryJob):
    """Refresh liveness only while this worker still owns the current lease."""
    if job.status != "running":
        return False
    now = datetime.now(timezone.utc)
    stmt = (update(DiscoveryJob)
            .where(DiscoveryJob.id == job.id,
                   DiscoveryJob.status == "running",
                   DiscoveryJob.lease_token == job.lease_token)
            .values(heartbeat_at=now))
    with db.no_autoflush:
        result = db.execute(stmt)
    if result.rowcount != 1:
        return False
    job.heartbeat_at = now
    db.flush()
    return True

def recover_stale_jobs(db: Session, stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS, now: datetime | None = None) -> dict:
    """Requeue expired running jobs up to retry limit; fail exhausted jobs.

    The caller owns the transaction and must commit. Row locks prevent competing
    PostgreSQL workers from recovering the same rows simultaneously.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=max(60, int(stale_after_seconds)))
    q = (db.query(DiscoveryJob)
         .filter(DiscoveryJob.status == "running")
         .filter(((DiscoveryJob.heartbeat_at.is_not(None)) & (DiscoveryJob.heartbeat_at < cutoff)) | ((DiscoveryJob.heartbeat_at.is_(None)) & (DiscoveryJob.started_at < cutoff)))
         .order_by(DiscoveryJob.id.asc())
         .with_for_update(skip_locked=True))
    recovered = {"requeued": 0, "failed": 0}
    for job in q.all():
        if job.retry_count < job.max_retries:
            job.retry_count += 1
            job.status = "queued"
            job.error = "Worker heartbeat expired; job automatically requeued."
            job.started_at = None
            job.heartbeat_at = None
            job.finished_at = None
            recovered["requeued"] += 1
        else:
            job.status = "failed"
            job.error = "Worker heartbeat expired; retry limit exhausted."
            job.finished_at = now
            job.heartbeat_at = None
            job.lease_token = None
            recovered["failed"] += 1
    db.flush()
    return recovered

def claim_next(db: Session):
    recover_stale_jobs(db)
    job = (db.query(DiscoveryJob)
           .filter(DiscoveryJob.status == "queued")
           .order_by(DiscoveryJob.created_at.asc(), DiscoveryJob.id.asc())
           .with_for_update(skip_locked=True)
           .first())
    if not job:
        return None
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.started_at = now
    job.heartbeat_at = now
    job.lease_token = uuid4().hex
    db.flush()
    return job

def consume_request(job: DiscoveryJob, count: int = 1):
    if count < 0 or job.requests_used + count > job.request_budget:
        raise RuntimeError("external request budget exceeded")
    job.requests_used += count

def finish_job(db: Session, job: DiscoveryJob, status: str = "completed", result: dict | None = None, error: str | None = None):
    """Finish only if the caller still holds the current lease (fencing stale workers)."""
    if status not in TERMINAL:
        raise ValueError("invalid terminal job status")
    now = datetime.now(timezone.utc)
    stmt = (update(DiscoveryJob)
            .where(DiscoveryJob.id == job.id,
                   DiscoveryJob.status.notin_(TERMINAL),
                   DiscoveryJob.lease_token == job.lease_token)
            .values(status=status, result=result or {}, error=error,
                    heartbeat_at=None, lease_token=None, finished_at=now))
    with db.no_autoflush:
        changed = db.execute(stmt).rowcount
    if changed != 1:
        raise RuntimeError("job lease lost or job is already terminal")
    job.status = status
    job.result = result or {}
    job.error = error
    job.heartbeat_at = None
    job.lease_token = None
    job.finished_at = now
    db.flush()
    return job
