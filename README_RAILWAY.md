# SMART MARKET V24.18.0 — GitHub + Railway + Android PWA

## Production architecture

Android browser/PWA → Railway FastAPI → Railway PostgreSQL/PostGIS.

The phone does **not** need Python, PostgreSQL, Passlib, Docker, or a local development environment.

## GitHub → Railway

1. Create a GitHub repository and upload this project to the repository root.
2. In Railway, create a project and choose **Deploy from GitHub Repo**.
3. Select the repository and production branch.
4. Railway detects the root `Dockerfile` and builds the application.
5. Add a PostgreSQL service in the same Railway project.
6. Set the web service `DATABASE_URL` to the PostgreSQL service's connection URL/reference.
7. Set a long random `SECRET_KEY`.
8. Set `ENVIRONMENT=production` and `DEBUG=false`.
9. Set `CORS_ORIGINS` to the public SMART MARKET domain (or the exact frontend origin).
10. Generate a Railway public domain.
11. Configure the service healthcheck as `/api/health` if it is not already picked up from `railway.toml`.

Railway supplies `PORT`; the Docker start command listens on `0.0.0.0:$PORT`.

## Required production variables

- `DATABASE_URL`
- `SECRET_KEY`
- `ENVIRONMENT=production`
- `DEBUG=false`
- `CORS_ORIGINS=https://YOUR-DOMAIN`
- `SESSION_TTL_HOURS=24`
- `RATE_LIMIT_PER_MINUTE=120`

Optional:

- `GOOGLE_MAPS_API_KEY`
- `FIRECRAWL_API_KEY`

## Authentication

V23.6.2 removed Passlib from the project and uses Argon2id through `argon2-cffi`. Existing Argon2 PHC hashes produced by Passlib remain compatible with Argon2 verification, so existing password hashes do not need a forced reset solely because of this migration.

## Android PWA

Open the deployed HTTPS domain in Chrome on Android and choose **Add to Home screen** / **Install app** when offered. The application includes a web manifest and service worker for the mobile shell.

## Database migrations

The container runs:

`alembic upgrade head`

before starting Uvicorn. Do not use `Base.metadata.create_all()` as a production migration mechanism.


## Production rate limiting (V24.16.6+)

Configure `REDIS_URL` as a Railway variable using a private Redis service. Production API rate limits require shared Redis; the app intentionally returns HTTP 503 if Redis is not configured or unavailable rather than applying inconsistent per-replica limits. See `RATE_LIMIT_SETUP.md`.
