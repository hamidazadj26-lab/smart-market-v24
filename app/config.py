from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = 'SMART MARKET'
    version: str = '24.21.0'
    environment: str = 'development'
    debug: bool = False
    secret_key: str = 'change-me-in-production'
    session_ttl_hours: int = 24
    database_url: str = 'sqlite:///./smart_market.db'
    default_market_name: str = ''
    cors_origins: str = 'http://localhost:8000'
    google_maps_api_key: str | None = None
    firecrawl_api_key: str | None = None
    divar_api_key: str | None = None
    discovery_timeout_seconds: float = 15.0
    discovery_max_results: int = 20
    rate_limit_per_minute: int = 120
    redis_url: str | None = None
    worker_heartbeat_key: str = 'smart-market:worker:heartbeat'
    worker_heartbeat_interval_seconds: float = 10.0
    worker_heartbeat_timeout_seconds: float = 30.0
    rate_limit_namespace: str = 'smart-market:api-rate-limit'
    discovery_request_budget: int = 50
    discovery_cache_ttl_seconds: int = 900
    discovery_max_retries: int = 3
    discovery_global_requests_per_minute: int = 120
    discovery_source_requests_per_minute: int = 30
    discovery_user_requests_per_minute: int = 60
    discovery_worker_poll_seconds: float = 2.0
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def cors_list(self):
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

@lru_cache
def get_settings():
    settings=Settings()
    if settings.environment.lower() == 'production':
        if not settings.secret_key or settings.secret_key == 'change-me-in-production':
            raise RuntimeError('SECRET_KEY must be explicitly configured in production.')
        if settings.database_url.startswith('sqlite'):
            raise RuntimeError('Production requires PostgreSQL; SQLite is not permitted.')
        if not settings.database_url.startswith(('postgresql://', 'postgresql+psycopg://', 'postgresql+psycopg2://')):
            raise RuntimeError('Production DATABASE_URL must be a PostgreSQL URL.')
        if not settings.redis_url:
            raise RuntimeError('Production requires REDIS_URL.')
        if any(origin.startswith('http://localhost') or origin.startswith('http://127.0.0.1') for origin in settings.cors_list):
            raise RuntimeError('Production CORS_ORIGINS must not contain localhost/127.0.0.1.')
    return settings
