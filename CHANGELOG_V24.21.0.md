# SMART MARKET V24.21.0

## Production Candidate Fixes

- Expanded matching decision engine to consume Product Fit, Capacity, Demand, Trust, Location, Price, Logistics, Evidence, Freshness and Buyer Reliability when observed.
- Unknown dimensions remain unknown and are never fabricated as zero/positive evidence.
- Matching explanations and persisted Opportunity score breakdown now expose the complete decision dimensions.
- Added source-backed FX resolver with direct/inverse pair support, expiry and provenance checks.
- Commercial offers now persist `fx_rate_id`; manual FX is no longer trusted by commercial comparison, benchmark, deal-decision, negotiation, trade-route and trade-optimizer flows.
- Added migration `0040_commercial_offer_fx_provenance`.
- Added separate `/api/live`, dependency-aware `/api/readiness`, and aggregate `/api/health` semantics.
- CI now includes dependency security audit, PostgreSQL/Redis integration, migration checks, Docker build and container smoke tests.
- Added V24.21 matching integrity tests.

## Verification

- Python compileall: PASS
- Alembic single head: `0040_commercial_offer_fx_provenance`
- Local test suite: **130 passed, 2 skipped**
- The two skips require live Redis/PostgreSQL services and are configured to run in CI.
- SQLite migration chain and API smoke (`/api/live`, `/api/readiness`, `/api/health`, `/api/setup/status`): PASS

## Deployment status

This package has **not** been pushed to GitHub or deployed to Railway by this release operation.
