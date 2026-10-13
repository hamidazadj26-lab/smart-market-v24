# SMART MARKET V24.21.2 — Mobile Portal & Action UX

## Included
- Branded SMART MARKET portal mark (SVG), PWA app icons (192×192 and 512×512), favicon and Apple touch icon.
- Branded setup/login screens and dashboard header.
- PWA manifest metadata updated for the Iran→Afghanistan trade opportunity platform.
- Service-worker/cache version bumped to 24.21.2 to reduce stale UI after deployment.
- Secondary action buttons have a high-contrast dark surface with yellow outline/focus state; disabled controls are visibly distinct.
- Discovery sources are only preselected when configured; unavailable sources are marked as requiring API/configuration.
- Includes the earlier scoring validation, CI database URL correction and regression tests.

## Verification performed locally
- `pytest`: 145 passed, 2 skipped (re-run during final audit on 2026-10-10).
- Python compileall: passed.
- `node --check static/app.js`: passed.
- This does not prove every live integration/button works on Railway. API keys, role permissions, data availability and backend endpoint errors still need live smoke tests after deployment.

## Deployment caution
Back up the current GitHub repository before applying the changes. This audited ZIP has project files directly at the archive root; there is no outer `sm20/` folder. Do not upload `.env` secrets. Preserve repository-specific secrets and environment variables in Railway. The GitHub `integration.yml` workflow must be located at `.github/workflows/integration.yml` (not `.github/workflows/workflows/integration.yml`). After applying the changes, commit them and verify CI, then test login, internal search, source discovery, advanced tools and mobile installation on the deployed service.

## Audit follow-up (2026-10-10)
- Corrected the login cookie `Secure` flag to normalize `ENVIRONMENT` casing, matching production configuration validation.
- Added a regression check for this production cookie-security contract.
- Added `AUDIT_INITIAL_V24.21.2.md` with verified local checks and explicit online/deployment limitations.


## Additional audit finding (2026-10-10)
- Corrected the integration workflow path inside this candidate package to `.github/workflows/integration.yml`. The live GitHub `main` branch still has the file one directory too deep; this package change has not been pushed to GitHub.
