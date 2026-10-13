"""Optional integration test against a dedicated disposable PostgreSQL database.

Set TEST_POSTGRES_URL explicitly to run this test. The database must be reserved
for tests because this module clears discovery_jobs before the concurrency check.
"""
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

POSTGRES_URL = os.getenv('TEST_POSTGRES_URL')
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason='TEST_POSTGRES_URL not configured; live PostgreSQL test not run')


def test_two_workers_cannot_claim_the_same_queued_job():
    from app.database import Base
    from app.models import DiscoveryJob
    from app.services.job_queue import create_job, claim_next

    engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with Session.begin() as db:
            db.query(DiscoveryJob).delete()
            create_job(db, 'postgres_concurrency_test', {'test': True}, max_retries=0)

        def claim():
            with Session() as db:
                job = claim_next(db)
                claimed_id = job.id if job else None
                db.commit()
                return claimed_id

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: claim(), range(2)))
        assert sum(value is not None for value in results) == 1
        assert len({value for value in results if value is not None}) == 1
    finally:
        with Session.begin() as db:
            db.query(DiscoveryJob).delete()
        engine.dispose()
