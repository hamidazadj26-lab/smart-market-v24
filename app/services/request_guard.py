"""API rate limiting with atomic Redis coordination and bounded local fallback.

Production deployments should configure REDIS_URL so limits are shared across
workers/replicas. Local fallback is intentionally limited to non-production.
"""
from collections import OrderedDict, deque
from datetime import datetime, timezone
from hashlib import sha256
from threading import Lock

from fastapi import HTTPException, Request

from ..config import get_settings
from ..security.auth import get_admin
from .rbac import enforce_mutation_permission

settings = get_settings()
_rate_window: OrderedDict[str, deque] = OrderedDict()
_rate_lock = Lock()
_RATE_MAX_KEYS = 10_000
_RATE_WINDOW_SECONDS = 60
_redis_client = None
_redis_init_lock = Lock()

# Atomic fixed-window counter. Expiry is set only on first increment, avoiding
# races between application replicas and keeping Redis storage self-cleaning.
_REDIS_LIMIT_SCRIPT = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return n
"""


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not settings.redis_url:
        return None
    with _redis_init_lock:
        if _redis_client is None:
            try:
                import redis
                client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1,
                                              socket_timeout=1, health_check_interval=30,
                                              decode_responses=True)
                client.ping()
                _redis_client = client
            except Exception:
                # Do not silently fall back to per-process limits in production.
                if settings.environment.lower() == 'production':
                    raise HTTPException(status_code=503, detail='Shared rate limiter unavailable')
                return None
    return _redis_client


def _local_limit(key: str, now: float):
    with _rate_lock:
        q = _rate_window.get(key)
        if q is None:
            cutoff = now - _RATE_WINDOW_SECONDS
            expired = [k for k, bucket in _rate_window.items()
                       if not bucket or bucket[-1] <= cutoff]
            for expired_key in expired:
                _rate_window.pop(expired_key, None)
            while len(_rate_window) >= _RATE_MAX_KEYS:
                _rate_window.popitem(last=False)
            q = deque()
            _rate_window[key] = q
        else:
            _rate_window.move_to_end(key)
        while q and now - q[0] >= _RATE_WINDOW_SECONDS:
            q.popleft()
        if len(q) >= settings.rate_limit_per_minute:
            raise HTTPException(429, 'تعداد درخواست‌ها در یک دقیقه بیش از حد مجاز است.')
        q.append(now)


def enforce_rate_limit(request: Request):
    # Do not trust X-Forwarded-For here: only the ASGI server/proxy configured
    # as trusted should set request.client.host. Hash the address in store keys.
    address = request.client.host if request.client else 'unknown'
    identity = sha256(address.encode('utf-8', 'replace')).hexdigest()[:32]
    now = datetime.now(timezone.utc).timestamp()
    client = _get_redis()
    if client is not None:
        window = int(now // _RATE_WINDOW_SECONDS)
        key = f'{settings.rate_limit_namespace}:{window}:{identity}'
        try:
            count = int(client.eval(_REDIS_LIMIT_SCRIPT, 1, key, _RATE_WINDOW_SECONDS + 2))
        except Exception:
            if settings.environment.lower() == 'production':
                raise HTTPException(status_code=503, detail='Shared rate limiter unavailable')
            _local_limit(identity, now)
            return
        if count > settings.rate_limit_per_minute:
            raise HTTPException(429, 'تعداد درخواست‌ها در یک دقیقه بیش از حد مجاز است.')
        return
    if settings.environment.lower() == 'production':
        raise HTTPException(status_code=503, detail='Production requires REDIS_URL for shared rate limiting')
    _local_limit(identity, now)


def auth(request: Request, db):
    enforce_rate_limit(request)
    admin = get_admin(request, db)
    return enforce_mutation_permission(request, admin)


def serialize(x):
    return {c.name: getattr(x, c.name) for c in x.__table__.columns}
