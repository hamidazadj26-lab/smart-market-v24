"""Live Redis integration test for shared atomic API rate limiting.

Set TEST_REDIS_URL to a dedicated Redis instance/database. The test creates
and removes only keys under a unique test namespace.
"""
import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

REDIS_URL = os.getenv('TEST_REDIS_URL')
pytestmark = pytest.mark.skipif(
    not REDIS_URL,
    reason='TEST_REDIS_URL not configured; live Redis integration test not run',
)


def test_shared_limit_is_enforced_across_independent_redis_clients(monkeypatch):
    redis = pytest.importorskip('redis')
    from app.services import request_guard

    client_a = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
    client_b = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
    namespace = f'smart-market:integration-test:{uuid.uuid4().hex}'
    try:
        assert client_a.ping() is True
        assert client_b.ping() is True
        monkeypatch.setattr(request_guard.settings, 'environment', 'test')
        monkeypatch.setattr(request_guard.settings, 'rate_limit_per_minute', 3)
        monkeypatch.setattr(request_guard.settings, 'rate_limit_namespace', namespace)
        req = lambda: SimpleNamespace(client=SimpleNamespace(host='198.51.100.42'))

        # Alternate independent client connections to model separate workers.
        monkeypatch.setattr(request_guard, '_get_redis', lambda: client_a)
        request_guard.enforce_rate_limit(req())
        monkeypatch.setattr(request_guard, '_get_redis', lambda: client_b)
        request_guard.enforce_rate_limit(req())
        monkeypatch.setattr(request_guard, '_get_redis', lambda: client_a)
        request_guard.enforce_rate_limit(req())
        monkeypatch.setattr(request_guard, '_get_redis', lambda: client_b)
        with pytest.raises(HTTPException) as exc:
            request_guard.enforce_rate_limit(req())
        assert exc.value.status_code == 429
    finally:
        for client in (client_a, client_b):
            try:
                keys = list(client.scan_iter(match=f'{namespace}:*'))
                if keys:
                    client.delete(*keys)
            finally:
                client.close()
