"""Production dependency health checks for SMART MARKET."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from ..config import get_settings
from ..database import engine


def check_database() -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        return False, type(exc).__name__


def check_redis() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.redis_url:
        return (settings.environment.lower() != "production", "not_configured")
    try:
        import redis
        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            health_check_interval=30,
            decode_responses=True,
        )
        client.ping()
        return True, "ok"
    except Exception as exc:
        return False, type(exc).__name__


def check_worker() -> tuple[bool, str]:
    """Worker liveness is coordinated through Redis, not process-local state."""
    settings = get_settings()
    if not settings.redis_url:
        return (settings.environment.lower() != "production", "not_configured")
    try:
        import redis
        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        raw = client.get(settings.worker_heartbeat_key)
        if not raw:
            return False, "missing"
        age = max(0.0, datetime.now(timezone.utc).timestamp() - float(raw))
        if age > settings.worker_heartbeat_timeout_seconds:
            return False, f"stale:{int(age)}s"
        return True, "ok"
    except Exception as exc:
        return False, type(exc).__name__


def check_migrations() -> tuple[bool, str]:
    """Compare the DB revision with Alembic's current repository head."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext

        base = Path(__file__).resolve().parents[2]
        cfg = Config(str(base / "alembic.ini"))
        cfg.set_main_option("script_location", str(base / "migrations"))
        script = ScriptDirectory.from_config(cfg)
        expected = script.get_current_head()
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
        if current != expected:
            return False, f"current={current or 'none'} expected={expected}"
        return True, expected
    except Exception as exc:
        return False, type(exc).__name__
