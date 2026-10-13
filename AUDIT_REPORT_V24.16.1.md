# Smart Market V24.16.0 — Audit & Hardening Report

Date: 2026-10-01
Audited source package: smart-market-v24.16.0-complete-hardening.zip
Working version: 24.16.0 + migration 0035 (maintenance hardening)

## Summary
- Initial suite: 111 tests passed.
- After hardening: 111 tests passed.
- Smoke test: passed against a fresh temporary SQLite database, including `/api/discovery/run`.
- Python compile check: passed.
- Alembic graph: one head, `0035_candidate_source_metadata`.
- No live PostgreSQL deployment or live third-party API integration was performed.

## Findings and changes
1. Fixed a discovery-run mismatch: extracted signal data was a dictionary, but candidate construction accessed it as an object.
2. Added migration `0035_candidate_source_metadata` for `source_url` and `source_title`, which were present in the ORM model but absent from the migration-created `discovery_candidates` table. The smoke test now exercises the route and migration path.
3. Changed job claiming to use `FOR UPDATE SKIP LOCKED` where supported, with deterministic ordering.
4. Changed discovery usage consumption to use row locking, a unique-window insert guarded by a savepoint, and a conditional atomic increment.
5. Tightened production Origin validation for state-changing requests; cookie-authenticated mutations are rejected when Origin is missing or untrusted.
6. Made `smoke_test.py` use a temporary database so repeated runs do not inherit an old administrator or state.
7. Updated migration-chain integrity test for the new head.
8. Removed Python bytecode and pytest cache artifacts from the delivery package. The provided `smart_market.db` was preserved.

## Additional hardening in this pass
- Bounded the process-local request limiter to 10,000 client buckets, added opportunistic expiry cleanup, and synchronized updates across threads. This does not make it cross-process.
- Hardened the backup helper: consistent SQLite snapshot plus integrity check; PostgreSQL archive catalog verification.

## Files changed
- `app/main.py`
- `app/services/request_guard.py`
- `scripts/backup_database.py`
- `app/services/job_queue.py`
- `app/services/discovery_controls.py`
- `app/routers/discovery.py`
- `smoke_test.py`
- `tests/test_project_integrity.py`
- `migrations/versions/0035_candidate_source_metadata.py` (new)

## Remaining risks / not yet verified
- The general API rate limiter is process-local (not shared across multiple workers/instances); memory is now bounded and updates are thread-safe, but distributed deployments should enforce limits at a shared gateway/store.
- Job retry/recovery of abandoned `running` jobs needs a complete lease/heartbeat policy.
- SQLite backups now use the online backup API and run `PRAGMA quick_check`; PostgreSQL dumps are checked with `pg_restore --list`. A full restore drill into a separate running application database is still recommended.
- PostgreSQL locking and concurrent budget behavior have not been exercised against a live PostgreSQL instance.
- External integrations have not been verified with real API keys (`Live integration not verified`).
- A full security review, browser-level mobile/RTL verification, production CORS/cookie deployment test, and end-to-end commercial transaction test remain.
- The source archive contains `smart_market.db`; review its data and deployment role before sharing the archive externally.

## Reproduction
From `sm_final/`:
- `python -m pytest -q`
- `python smoke_test.py`
- `python -m compileall -q app migrations scripts`
- `alembic heads`
