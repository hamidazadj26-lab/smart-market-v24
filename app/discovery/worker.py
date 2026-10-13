"""Durable discovery worker. Run with: python -m app.discovery.worker"""
from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from app.config import get_settings
from app.database import SessionLocal
from app.models import DiscoveryJob, Admin
from app.schemas import ExternalDiscoveryIn
from app.services.job_queue import claim_next, finish_job
from app.routers.remaining import _run_external_discovery

async def process_one():
    db=SessionLocal()
    try:
        job=claim_next(db)
        if not job:
            return False
        db.commit(); db.refresh(job)
        lease_token = job.lease_token
        admin=db.get(Admin,job.created_by) if job.created_by else None
        try:
            await _run_external_discovery(ExternalDiscoveryIn(**job.payload),None,db,job,admin)
        except Exception as exc:
            db.rollback(); current=db.get(DiscoveryJob,job.id)
            # Do not let an expired worker overwrite a retry claimed by another worker.
            if current and current.status == 'running' and current.lease_token == lease_token:
                try:
                    finish_job(db,current,'failed',error=str(exc)); db.commit()
                except RuntimeError:
                    db.rollback()
        return True
    finally:
        db.close()

async def _heartbeat(settings):
    import redis
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2, decode_responses=True)
    while True:
        client.set(settings.worker_heartbeat_key, str(datetime.now(timezone.utc).timestamp()), ex=max(10, int(settings.worker_heartbeat_timeout_seconds)))
        await asyncio.sleep(max(2.0, settings.worker_heartbeat_interval_seconds))


async def main():
    settings=get_settings()
    if not settings.redis_url:
        raise RuntimeError("Worker requires REDIS_URL")
    heartbeat_task = asyncio.create_task(_heartbeat(settings))
    try:
        while True:
            worked=await process_one()
            if not worked:
                await asyncio.sleep(max(0.2,settings.discovery_worker_poll_seconds))
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

if __name__=='__main__':
    asyncio.run(main())
