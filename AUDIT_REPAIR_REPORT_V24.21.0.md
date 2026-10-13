# SMART MARKET V24.21.0 — Audit and Repair Candidate

Date: 2026-10-09
Repository inspected read-only: `hamidazadj26-lab/smart-market-v24`
Reference branch: `main`

## Scope and access status

- Read access to selected files on GitHub `main` succeeded.
- The repository currently exposes only the `main` branch in branch search.
- Creating `fix/v24.21.0-scoring-validation` failed with GitHub API HTTP 403 (`Resource not accessible by integration`). The GitHub integration reports no active installations.
- Consequently, this candidate has **not** been committed or pushed to GitHub, no Pull Request was created, and no Railway deployment was performed.
- The supplied V24.21.0 ZIP was used for executable local tests; selected live GitHub files were also reviewed. Before merging, apply/review this candidate against the current branch and inspect the final diff.

## Findings addressed in this candidate

### P1 — Scoring accepts invalid custom weights

`app/opportunity/scoring.py` merged arbitrary keys and values into the weight dictionary. Negative, non-finite, non-numeric, or unknown weights could corrupt the denominator and evidence coverage. All-zero weights were silently treated as a fallback denominator, hiding invalid configuration.

Fix: validate the mapping, reject unknown dimensions and booleans/non-numeric values, reject negative and non-finite weights, and require a positive total. Non-finite observed dimension scores are rejected. Buyer reliability used in confidence is now the same normalized value exposed in the score dimensions.

Regression tests: `tests/test_opportunity_scoring_validation.py` (14 tests).

### P1 — PWA cache version was stale

The backend identifies itself as V24.21.0, while `static/index.html` and `static/sw.js` referenced V24.20.0 assets/cache. This could cause stale front-end assets to remain cached after deployment.

Fix: synchronize HTML asset query versions, service-worker cache name/assets, and the mobile contract test to V24.21.0.

### P1 — CI migration check did not target PostgreSQL

The integration workflow starts PostgreSQL and checks connectivity using `TEST_POSTGRES_URL`, but the Alembic migration step did not set `DATABASE_URL`. The app configuration therefore defaults that step to SQLite despite the step name claiming PostgreSQL migration verification.

Fix: explicitly set `DATABASE_URL` to the CI PostgreSQL service for the migration-chain verification step. The GitHub Actions run must confirm the PostgreSQL migration and `alembic check` results; those live-service steps were not executed in this local environment.

## Local verification performed on this candidate

- `pytest -q`: **144 passed, 2 skipped**.
- `python -m compileall -q app migrations scripts`: passed.
- `node --check static/app.js`: passed.
- `alembic heads`: passed; head is `0040_commercial_offer_fx_provenance`.
- `alembic history`: passed.
- YAML parse with PyYAML BaseLoader: checked separately for syntax; GitHub Actions semantics still require CI execution.

## Not verified

- PostgreSQL migration execution against a live PostgreSQL service.
- Redis integration against a live Redis service.
- `pip-audit` against the current vulnerability database.
- Docker build/container smoke test.
- Railway deployment, runtime logs, or the deployed revision.
- End-to-end operation of external discovery providers or Google Maps without configured credentials.

## Status

`READY WITH LIMITATIONS` for the local tested repair candidate only; **not a claim that production is ready**. GitHub write access and live integration/deployment checks remain blocked or unverified.
