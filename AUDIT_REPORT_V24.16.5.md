# Smart Market V24.16.5 — Lease Fencing & Job Reliability

## Changes
- Added `lease_token` to discovery jobs with migration `0037_job_lease_fencing`.
- Each claim receives a unique lease token. Stale-job recovery clears the expired token before requeueing.
- Heartbeats now use a conditional database update that only succeeds while the caller still owns the current running lease.
- Job completion is fenced by the lease token, preventing an expired worker from overwriting the result of a newer retry.
- Worker exception handling preserves the original lease token and will not mark a job failed after ownership has moved to another worker.
- External discovery checks lease ownership before and after external fetches.
- Added a regression test proving an expired worker cannot heartbeat or finish a reclaimed job.

## Verification in this environment
- `pytest -q`: 115 passed, 1 skipped. The skipped test is the opt-in PostgreSQL integration test because `TEST_POSTGRES_URL` was not configured.
- `python smoke_test.py`: SMOKE OK.
- `python -m compileall -q app migrations scripts`: passed.
- `alembic heads`: `0037_job_lease_fencing` is the sole head.

## Remaining limitations
- A live PostgreSQL concurrency test was not run; SQLite tests do not validate PostgreSQL row-lock behavior.
- The process-local API rate limiter is not shared across multiple application workers/instances.
- Production deployment, external API credentials, full cookie/CORS review, and full restore drill still need environment-specific verification.
