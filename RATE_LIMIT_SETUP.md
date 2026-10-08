# Production API rate-limit setup

Smart Market V24.16.6 uses Redis to share API rate limits across application workers and replicas.

1. Provision a private Redis service with authentication and TLS where supported.
2. Set `REDIS_URL` in the production deployment environment (do not commit credentials to source control). Example shape: `rediss://:<password>@<host>:<port>/<db>`.
3. Optionally set `RATE_LIMIT_NAMESPACE` to a unique prefix for this deployment. Default: `smart-market:api-rate-limit`.
4. Keep `RATE_LIMIT_PER_MINUTE` at the intended policy value; default is 120.
5. Deploy and confirm Redis connectivity, then test that requests distributed across two application replicas share the same limit.
6. Monitor HTTP 503 responses indicating the shared limiter is unavailable and HTTP 429 responses indicating limits are being applied.

Production deliberately fails closed if `REDIS_URL` is absent or Redis is unavailable. Local development can use the bounded in-memory fallback.

Do not trust forwarded client IP headers unless the reverse proxy is explicitly configured as trusted by the ASGI server.
