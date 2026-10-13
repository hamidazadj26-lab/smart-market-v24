# SMART MARKET V24.23.0 — Pre-transfer and deployment handoff

## Release identity
- Candidate: SMART MARKET V24.23.0 — Interactive Commercial Intelligence Map
- Intended destination: `hamidazadj26-lab/smart-market-v24`, branch `main`
- This archive is a prepared release candidate; it has **not** been pushed to GitHub or deployed to Railway.

## Local verification performed for this package
- `python -m pytest -q`: 159 passed, 2 skipped.
- Python compile checks and JavaScript syntax check were recorded in the V24.23.0 audit report.
- ZIP archive integrity must be checked against the SHA-256 manifest accompanying this release.
- No `.env`, database files, private keys, or files with names matching secret/database artifacts were found in the source tree during the pre-transfer scan.

## Before upload
1. Keep a backup of the current GitHub repository and do not delete it.
2. Upload this release to a **new branch** such as `release/v24.23.0` if possible. If using a clean replacement repository, preserve the current repository until acceptance tests pass.
3. Upload the *contents* of this archive to the repository root, not the ZIP file itself. The root should contain `Dockerfile`, `requirements.txt`, `railway.toml`, `alembic.ini`, `app/`, `migrations/`, `static/`, `tests/`, and `.github/workflows/integration.yml`.
4. Do not upload `.env` or production credentials. Configure secrets only in Railway environment variables.
5. Confirm the GitHub upload preserved folder paths and that no accidental top-level wrapper directory was added.
6. Wait for GitHub Actions to complete. Resolve any failed CI, migration, dependency-audit, or container-smoke checks before merging to `main`.

## GitHub browser upload constraints
GitHub's browser upload supports up to 100 files per upload, and each file must be below the documented browser limit. The release contains more than 100 files, so do not try to commit it as one upload. On Android, uploading nested directories and maintaining their exact paths may be awkward; a Git-aware upload method (GitHub Desktop, Codespaces terminal, or a trusted local Git client) is safer than manually creating hundreds of files. If browser upload is the only option, work in small batches and verify every path; do not delete the old files until the new tree has been checked.

## Railway acceptance checks after merge
1. Confirm deployment uses the repository root Dockerfile and the expected branch.
2. Set production `DATABASE_URL`, a strong unique `SECRET_KEY`, `ENVIRONMENT=production`, `DEBUG=false`, correct `CORS_ORIGINS`, and authenticated/TLS `REDIS_URL` as applicable.
3. Confirm database backups exist before running migrations. Do not copy a local SQLite database into production automatically.
4. Verify deployment status succeeds and test `/api/live`, `/api/readiness`, and `/api/health`.
5. Test login, dashboard, product/manufacturer/customer/demand flows, discovery, Trade Radar, and authenticated `GET /api/intelligence/map.geojson`.
6. Open the portal on an Android browser; test RTL layout, layer toggles, filters, map tiles/CDN availability, and PWA behavior.
7. Confirm OSIRIS remains disabled unless its feed URLs and access are deliberately configured. Do not treat discovery candidates as verified buyers.

## Known limitations / gates
- The current GitHub repository could not be read through the connected GitHub tool (404), so this candidate has not been diffed against the actual remote head.
- Tests executed here do not establish that live Railway, production PostgreSQL/Redis, external map tiles, or live OSIRIS feeds work.
- The two skipped tests must be reviewed in CI context; skipped tests are not passes for the skipped behavior.
- OpenStreetMap standard tiles are subject to their usage policy and are not a guaranteed high-volume production tile service.

## Suggested commit message
`Release SMART MARKET V24.23.0: intelligence map and trade radar`
