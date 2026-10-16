# V24 Release Readiness — Evidence-Based Gate

This checklist is the release gate for the Smart Market V24 candidate. It deliberately separates CI success from production readiness.

## Current verified status (2026-10-16)

- [x] Latest integration run [38927844741](https://github.com/hamidazadj26-lab/smart-market-v24/actions/runs/38927844741) completed successfully at commit `db8998ffb816dbce6009a3d4756893165e17eeec`; it ran the full test suite, mobile/PWA contract, migration chain through `0044_align_orm_single_column_indexes`, blocking `alembic check`, dependency audit, Docker build, and container smoke test.
- [x] Revision `0043_nullable_derived_offer_totals` removes server-side zero defaults from the derived CFR/landed totals without rewriting ambiguous historical values.
- [x] ORM-to-migration schema drift is reconciled for the current branch metadata. Revision `0044_align_orm_single_column_indexes` adds the missing single-column indexes while preserving legacy composite indexes; the latest blocking `alembic check` completed with `No new upgrade operations detected`. The audit matches index names by exact table/column/order/uniqueness shape and does not ignore shape changes. A SQLAlchemy warning about reflecting the PostGIS `geography` column remains visible in logs and should be monitored; spatial columns/indexes are intentionally managed by migrations rather than ORM metadata.
- [ ] No production deployment or production database migration has been performed as part of this branch.
- [ ] External discovery sources, credentials, and actual Iran→Afghanistan buyer/supplier data have not been proven operational by the CI checks.

## Blocking work before production

### P0 — Database correctness
- [x] Capture and retain the machine-readable schema-drift evidence from the isolated PostGIS migration-check run; review-only autogeneration produced no operations at the current head.
- [x] Re-run blocking `alembic check` against the isolated PostGIS database at the current branch head; it reports no new upgrade operations.
- [ ] Classify each difference into: (a) semantic constraint/nullability mismatch, (b) missing performance index, or (c) equivalent naming/representation difference.
- [ ] For nullable-to-non-null changes, add a reviewed backfill and preflight query; fail with an actionable message if invalid legacy rows exist. Never silently discard or invent commercial data.
- [ ] Reconcile unique constraints versus unique indexes only after verifying duplicates and existing production schema behavior.
- [x] Keep the schema-drift audit blocking in CI on this branch; do not restore `continue-on-error` to make a red check appear green.
- [x] Reconcile the reported index metadata/migration differences in a reviewed migration, preserving useful composite indexes and exact index-shape/uniqueness comparisons; the blocking audit now passes.

### P0 — Release and deployment safety
- [ ] Confirm the target Railway project/service, start command, health/readiness routes, and required environment variables.
- [ ] Run migrations on a disposable/staging database first and verify `alembic current` equals the single `alembic heads` revision.
- [ ] Verify rollback/recovery and database backup procedures before any production migration.
- [ ] Keep the existing production service unchanged until staging smoke tests and explicit deployment approval.

### P1 — Real business workflow (not just a demo)
- [ ] Prove the complete workflow with persisted records: product → supplier candidates → buyer candidates → evidence-backed demand → ranked opportunity → landed-cost estimate → follow-up/deal status.
- [ ] Ensure every buyer/demand assertion carries source, evidence, confidence, and last-checked/freshness information; distinguish a business listing from evidence of purchase intent.
- [ ] Validate landed-cost calculations against hand-calculated fixtures, including currencies/FX provenance, duties, freight, fees, missing inputs, and zero/negative values.
- [ ] Verify source adapters honestly report configured/available/failed states; no fabricated discovery results or success indicators.
- [ ] Test the mobile RTL UI against real API responses and errors, including empty states, slow network, authentication expiry, and small screens.

### P2 — Operational readiness
- [ ] Verify structured logs, actionable error reporting, background-job retry/lease behavior, and duplicate-job protection.
- [ ] Verify authentication, session revocation/expiry, authorization boundaries, secret configuration, and dependency security.
- [ ] Add a staging smoke-test record with commit SHA, migration head, test outcome, and manual workflow evidence.

## Release decision

**Current decision: NOT READY FOR PRODUCTION.** The latest CI run verifies the migration chain and passes the blocking ORM/schema drift audit on an isolated PostGIS database. It does not prove live Railway configuration, production backup/rollback readiness, external discovery credentials, or the end-to-end Iran→Afghanistan commercial workflow. Keep this branch unmerged and production unchanged until staging checks and explicit deployment approval.
