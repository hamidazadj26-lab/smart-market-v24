# Smart Market V24.16.8 — Live integration test readiness

## Changes
- Added `tests/test_live_redis_rate_limit.py` to exercise the real Redis Lua counter through two independent Redis connections.
- Added `.github/workflows/integration.yml` to start Redis and PostGIS/PostgreSQL service containers, verify connectivity, run the complete test suite, and compile the app/migrations.
- Added `INTEGRATION_TESTING_V24.16.8.md` with safe execution instructions and clear test prerequisites.
- Updated application version to 24.16.8.

## Local verification
- Live Redis/PostgreSQL servers and Docker are not available in the current environment. Real integration is therefore not claimed as passed.
- The regular unit/regression suite can still be run locally; integration tests skip unless dedicated test URLs are configured.

## Remaining before production approval
- Run the CI workflow and inspect its actual result; fix any live-service failures.
- Verify Redis shared limits with two actual app replicas behind the production proxy/load balancer.
- Verify PostgreSQL job claims under repeated concurrent load.
- Exercise backup restoration and deployment rollback in staging.
- Inspect `smart_market.db` before sharing the archive externally.
