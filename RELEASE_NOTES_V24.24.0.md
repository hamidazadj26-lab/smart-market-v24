# SMART MARKET V24.24.0 — Schema parity and trustworthy commercial totals

## Changes
- Preserve unknown CFR and landed-cost totals as `NULL` until the required inputs are available; remove database server defaults that could turn unknown derived values into zero.
- Add migration `0044_align_orm_single_column_indexes` for the missing single-column ORM indexes identified by the isolated PostgreSQL/PostGIS schema audit.
- Preserve legacy composite indexes used for entity resolution, FX-pair lookup, opportunity recency, discovery-job recovery, and market-price history.
- Keep `alembic check` as a blocking CI gate and align the migration-chain integrity test with revision `0044`.
- Synchronize API and PWA cache version metadata to `24.24.0`.

## Verification evidence
- Integration run [38927844741](https://github.com/hamidazadj26-lab/smart-market-v24/actions/runs/38927844741) passed at code commit `db8998ffb816dbce6009a3d4756893165e17eeec`: 212 tests passed, 7 mobile/PWA contract tests passed, migration chain reached `0044`, blocking `alembic check` reported `No new upgrade operations detected`, dependency audit passed, Docker image built, and container smoke test passed.
- A follow-up commit updates release-readiness documentation and version labels; its own CI run must also pass before this candidate is considered verified at the current head.

## Release limitations
- **Not approved for production.** No Railway deployment or production database migration was performed.
- Before release, configure and verify the separate worker service, real production secrets/Redis/PostgreSQL connection, backups and rollback, external discovery credentials, and the complete evidence-backed Iran→Afghanistan trade workflow in staging.
- The CI log contains a SQLAlchemy warning while reflecting the PostGIS `geography` column; the schema audit passes, but spatial-query behavior should still be covered by a targeted staging smoke test.
