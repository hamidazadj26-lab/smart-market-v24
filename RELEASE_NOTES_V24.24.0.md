# SMART MARKET V24.24.0 — Schema parity and trustworthy commercial totals

## Changes
- Preserve unknown CFR and landed-cost totals as `NULL` until the required inputs are available; remove database server defaults that could turn unknown derived values into zero.
- Add migration `0044_align_orm_single_column_indexes` for the missing single-column ORM indexes identified by the isolated PostgreSQL/PostGIS schema audit.
- Preserve legacy composite indexes used for entity resolution, FX-pair lookup, opportunity recency, discovery-job recovery, and market-price history.
- Keep `alembic check` as a blocking CI gate and align the migration-chain integrity test with revision `0044`.
- Synchronize API and PWA cache version metadata to `24.24.0`.

## Verification evidence
- Integration run [38929097538](https://github.com/hamidazadj26-lab/smart-market-v24/actions/runs/38929097538) passed at commit `8d3ac2d71488af883b3d81ac9a04317846c8a3ae`: 212 tests passed, 7 mobile/PWA contract tests passed, migration chain reached `0044`, blocking `alembic check` reported `No new upgrade operations detected`, dependency audit passed, Docker image built, and container smoke test passed.
- The mobile/PWA contract tests now derive the expected cache version from `app/config.py`, preventing future releases from failing solely because tests hard-coded an older version.

## Release limitations
- **Not approved for production.** No Railway deployment or production database migration was performed.
- Before release, configure and verify the separate worker service, real production secrets/Redis/PostgreSQL connection, backups and rollback, external discovery credentials, and the complete evidence-backed Iran→Afghanistan trade workflow in staging.
- The CI log contains a SQLAlchemy warning while reflecting the PostGIS `geography` column; the schema audit passes, but spatial-query behavior should still be covered by a targeted staging smoke test.
