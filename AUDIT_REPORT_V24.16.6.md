# Smart Market V24.16.6 — Shared Rate Limiting Hardening

## Problem addressed
The API rate limiter previously stored request counters only in process memory. That made limits independent across worker processes/replicas and allowed memory pressure from many distinct client addresses.

## Changes
- Added an atomic Redis fixed-window limiter using a single Lua `INCR`/`EXPIRE` operation.
- Redis keys use a SHA-256-derived client identifier (not the raw IP), a namespace, and a 60-second time bucket; TTL prevents unbounded Redis key growth.
- The application does not trust `X-Forwarded-For` directly; `request.client.host` must be supplied by the ASGI server / trusted proxy configuration.
- In production, missing/unavailable Redis fails closed with HTTP 503 rather than silently degrading to per-process limits.
- Non-production environments retain a thread-safe, bounded in-memory fallback for local development.
- Added `REDIS_URL` and `RATE_LIMIT_NAMESPACE` configuration; pinned redis client dependency.

## Deployment
Set `REDIS_URL` to a private, authenticated Redis endpoint in the production environment before deploying. Use a managed Redis service or private network. Ensure the deployment's ASGI proxy settings are configured correctly before relying on client IP rate limits. If Redis is unavailable, rate-limited endpoints intentionally return 503 in production; configure monitoring/alerts for this condition.

## Verification
- `pytest -q`: 118 passed, 1 skipped.
- `python smoke_test.py`: `SMOKE OK`.
- `python -m compileall -q app migrations scripts`: passed.
- `alembic heads`: `0037_job_lease_fencing (head)`.
- Added tests for atomic shared-counter invocation, per-client separation, rate threshold enforcement, and fail-closed production behavior.

## Limitations
- A live Redis service was not available in this environment; Redis behavior was verified using a deterministic fake client, not a live integration test.
- A live PostgreSQL concurrency test has not been run.
- Production deployment is not fully verified until REDIS_URL is configured and Redis/ASGI proxy behavior is tested in the target environment.
