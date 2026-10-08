# SMART MARKET V24.18.0 — GitHub + Railway Runbook

## Target architecture

Mobile browser / Android PWA → Railway web service → PostgreSQL + Redis.

The repository is the single source of truth for application code and infrastructure configuration. Runtime secrets and databases stay outside Git.

## GitHub

Create a **private** repository named `smart-market` (or another chosen name). Push the project root directly into the repository. Do not commit:

- `.env` or API credentials
- `*.db`, `*.sqlite*`
- logs, caches, virtual environments

The repository contains a GitHub Actions workflow at `.github/workflows/integration.yml`. Pull requests and pushes to `main` run Redis/PostgreSQL integration tests, the full pytest suite, migration-head checks, and Python compilation.

Recommended branch policy:

- `main` — releasable code
- `develop` — integration branch
- `feature/*` — isolated changes

## Railway

Create a private Railway project named `smart-market`. Use the GitHub repository as the source of the web service.

### Required runtime services

1. FastAPI web service from the GitHub repository.
2. Managed PostgreSQL.
3. Redis with authentication/TLS where available.

### Required application variables

- `DATABASE_URL`
- `SECRET_KEY`
- `ENVIRONMENT=production`
- `DEBUG=false`
- `CORS_ORIGINS=https://YOUR-DOMAIN`
- `SESSION_TTL_HOURS=24`
- `RATE_LIMIT_PER_MINUTE=120`
- `REDIS_URL=rediss://...`

Optional variables are documented in `.env.example`.

### Deployment behavior

`railway.toml` and `Dockerfile` run Alembic migrations before Uvicorn. The Railway health check is `/api/health`.

After every deployment, verify the deployment reaches `SUCCESS` and then verify `/api/health` and authenticated login from a real mobile browser.

## Mobile-first acceptance checklist

- RTL Persian layout at 320px–430px viewport widths
- 44px+ touch targets
- No horizontal overflow on primary screens
- Forms use 16px inputs to avoid mobile browser zoom
- Bottom navigation works with keyboard and touch
- PWA manifest + service worker load successfully
- Installable from HTTPS on Android/compatible browsers
- Offline shell does not cache API responses

## Data safety

Do not migrate the local `smart_market.db` into production automatically. Production data must live in Railway PostgreSQL. Backups and restore drills must be performed against a separate verification target before declaring production-ready.
