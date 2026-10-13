# Smart Market V24.16.8 — Live integration testing

## What changed
- Added an opt-in live Redis integration test that uses two independent Redis client connections and verifies a shared request limit.
- Added CI workflow provisioning disposable Redis 7 and PostGIS/PostgreSQL 16 services, checking service connectivity, running the complete suite with live integration variables, and compiling application/migration code.
- Bumped the application version to 24.16.8.

## Run live tests locally
Use dedicated disposable services and do not point `TEST_POSTGRES_URL` at a production database. The PostgreSQL job-claim test deletes rows from `discovery_jobs` as part of its test setup/cleanup.

```bash
export TEST_REDIS_URL='redis://localhost:6379/15'
export TEST_POSTGRES_URL='postgresql+psycopg://smart_test:test-only-password@localhost:5432/smart_market_test'
pytest -q
```

The Redis integration test creates keys under a unique namespace and deletes only that namespace. The PostgreSQL test must run only against a dedicated disposable test database.

## Verification status in the current editing environment
The current environment does not provide Docker, a local Redis server, or a PostgreSQL server, so live-service tests cannot be truthfully marked as passed here. Without `TEST_REDIS_URL`, the Redis integration test is skipped; without `TEST_POSTGRES_URL`, the PostgreSQL concurrency test is skipped. The CI workflow is configured to run both against real disposable services on GitHub Actions, but its remote result must be checked after push/run.
