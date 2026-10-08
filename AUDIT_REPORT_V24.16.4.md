# Smart Market V24.16.4 — Job Recovery & Concurrency Audit

## Implemented
- Added `heartbeat_at` to `discovery_jobs` and migration `0036_job_heartbeat_recovery`.
- Added stale-job recovery: jobs with expired heartbeat are requeued while retry budget remains; exhausted jobs are marked failed.
- Job claiming refreshes heartbeat and uses row locking with `SKIP LOCKED` on databases that support it.
- Discovery execution updates heartbeat around external fetch operations.
- Fixed an unbound `admin` variable in the discovery-jobs listing endpoint.
- Added tests for stale-job retry/exhaustion and fresh-heartbeat protection.
- Added an opt-in PostgreSQL concurrency integration test (`TEST_POSTGRES_URL`) for a dedicated disposable database.

## Verification performed in this environment
- `pytest -q`: 114 passed before adding the optional PostgreSQL integration test.
- `python -m compileall -q app migrations scripts`: passed.
- `alembic heads`: `0036_job_heartbeat_recovery` is the sole head.
- `python smoke_test.py`: `SMOKE OK`, including fresh SQLite migrations and API flow.
- Live PostgreSQL concurrency was not run because no `TEST_POSTGRES_URL` was provided. The optional test is skipped unless explicitly configured.

## Remaining limitations
- Heartbeats are refreshed around external calls; a single fetcher that blocks longer than the 1-hour stale threshold without yielding/returning could still be reclaimed. Use cancellable fetch timeouts or a dedicated heartbeat task for stricter leases.
- PostgreSQL locking behavior must be validated in a real isolated PostgreSQL environment before production deployment.
- This audit does not certify the entire application as production-secure.
