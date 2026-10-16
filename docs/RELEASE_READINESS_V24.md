# V24 Release Readiness — Evidence-Based Gate

This checklist is the release gate for the Smart Market V24 candidate. It deliberately separates CI success from staging evidence and production readiness.

## Current verified status (2026-10-16)

- [x] Latest integration run [38929370793](https://github.com/hamidazadj26-lab/smart-market-v24/actions/runs/38929370793) completed successfully at commit `675278ba02136e0c1785dfa3325066c6f7284e4a`. The integration job, full test suite, mobile/PWA contract, PostgreSQL migration chain, blocking schema-drift gate, dependency audit, production container build, and container smoke test all passed. The run is green; do not infer live-service readiness from it.
- [x] Revision `0043_nullable_derived_offer_totals` removes server-side zero defaults from derived CFR/landed totals without rewriting ambiguous historical values.
- [x] Revision `0044_align_orm_single_column_indexes` adds missing single-column indexes while preserving legacy composite indexes. Blocking `alembic check` reports `No new upgrade operations detected`. The audit compares exact table/column/order/uniqueness shape. A SQLAlchemy warning reflecting PostGIS `geography` remains; run a targeted spatial-query smoke test in staging.
- [x] Railway configuration was inspected read-only on 2026-10-16; no Railway settings were changed and no deployment was triggered.
- [ ] No production deployment or production database migration has been performed for this branch.
- [ ] External discovery sources, credentials, and actual Iran→Afghanistan buyer/supplier data have not been proven operational by CI.

## Railway audit — blocking findings (2026-10-16)

The available Railway connection points to workspace `111hh999tt's Projects`, project `perfect-determination`, environment `production`, service `smart-market-v19`. This is **not** the V24 candidate deployment.

- The live service source is `111Hh999Tt/smart-market-v19` on `main`, deployed 2026-09-30 at commit `38d1e8104bdaaeb24a9c7f41ebfd92789981d014`; latest deployment reports SUCCESS.
- Only a `production` environment was returned; no staging environment exists in that project.
- The project has one service and no separate discovery worker service.
- Live service build configuration reports `RAILPACK`, while the V24 candidate's `railway.toml` declares `DOCKERFILE`. This confirms the inspected service is not configured from the V24 candidate's checked-in deployment config.
- The only user-defined service variable visible by name was `GOOGLE_MAPS_API_KEY`; required V24 production settings such as `SECRET_KEY`, PostgreSQL `DATABASE_URL`, `REDIS_URL`, `ENVIRONMENT=production`, and non-localhost `CORS_ORIGINS` were not present in the returned variable-name list. Secret values were not read or recorded.
- The V24 candidate has a separate worker image (`Dockerfile.worker`) and expects Redis-backed job processing/heartbeat. That worker is not deployed in the inspected Railway project.

**Decision:** do not repoint or redeploy the existing `smart-market-v19` production service. The available Railway project is the wrong source and has no staging environment. A safe V24 staging run requires a separate staging project/environment wired to `hamidazadj26-lab/smart-market-v24`, a disposable PostgreSQL/PostGIS database, Redis, a separate worker service, and staging-only secrets. This audit did not create resources or incur new deployment costs.

## Blocking work before production

### P0 — Deployment and database safety
- [ ] Confirm/create the correct isolated V24 staging target; never repoint the existing V19 production service.
- [ ] Configure API and worker services from the same reviewed V24 commit; verify the API uses the Dockerfile/config-as-code as intended and the worker command is `python -m app.discovery.worker`.
- [ ] Set staging-only `SECRET_KEY`, PostgreSQL `DATABASE_URL`, `REDIS_URL`, `ENVIRONMENT=production`, and correct `CORS_ORIGINS`; add external source keys only when available. Do not copy production secrets into staging.
- [ ] Run migrations against the disposable staging database; verify `alembic current` equals the single `alembic heads` revision and `/api/readiness` plus `/api/health` report the expected checks.
- [ ] Verify database backup and restore/rollback procedures before any production migration.
- [ ] Run a targeted PostGIS spatial-query smoke test and capture evidence.

### P1 — Real Iran→Afghanistan business workflow
- [ ] Prove a persisted end-to-end path: product → supplier candidates → buyer candidates → evidence-backed demand → ranked opportunity → landed-cost estimate → follow-up/deal status.
- [ ] Ensure every buyer/demand assertion has source, evidence, confidence, and freshness/last-checked information; distinguish a business listing from evidence of purchase intent.
- [ ] Validate landed-cost calculations against hand-calculated fixtures for currencies/FX provenance, duties, freight, fees, missing inputs, and zero/negative values.
- [ ] Verify source adapters report configured/available/failed states honestly; no fabricated discovery results or success indicators.
- [ ] Test mobile RTL UI with real API responses and error cases, including empty states, slow network, authentication expiry, and small screens.

### P2 — Operational readiness
- [ ] Verify structured logs, actionable errors, background-job retries/leases, duplicate-job protection, authentication/session expiry and revocation, and authorization boundaries.
- [ ] Add a staging smoke-test record with commit SHA, migration head, API/worker health, test outcome, and manual workflow evidence.

## Release decision

**Current decision: NOT READY FOR PRODUCTION.** CI and schema parity are green, but the available Railway connection targets the older V19 production service, not V24. Do not merge this branch to `main` or alter production until the correct isolated staging target is configured, the end-to-end workflow and PostGIS smoke test pass, backup/rollback are verified, and deployment is explicitly approved.
