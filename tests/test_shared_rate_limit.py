from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import request_guard


class FakeRedis:
    def __init__(self):
        self.counts = {}
        self.calls = []

    def eval(self, script, numkeys, key, ttl):
        self.calls.append((script, numkeys, key, ttl))
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


def req(ip='192.0.2.10'):
    return SimpleNamespace(client=SimpleNamespace(host=ip))


def test_redis_limiter_uses_shared_atomic_counter(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(request_guard, '_get_redis', lambda: fake)
    monkeypatch.setattr(request_guard.settings, 'environment', 'test')
    monkeypatch.setattr(request_guard.settings, 'rate_limit_per_minute', 2)
    monkeypatch.setattr(request_guard.settings, 'rate_limit_namespace', 'test:limit')
    request_guard.enforce_rate_limit(req())
    request_guard.enforce_rate_limit(req())
    with pytest.raises(HTTPException) as exc:
        request_guard.enforce_rate_limit(req())
    assert exc.value.status_code == 429
    assert fake.calls[0][1] == 1
    assert fake.calls[0][3] == 62


def test_redis_counter_isolated_by_client(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(request_guard, '_get_redis', lambda: fake)
    monkeypatch.setattr(request_guard.settings, 'environment', 'test')
    monkeypatch.setattr(request_guard.settings, 'rate_limit_per_minute', 1)
    request_guard.enforce_rate_limit(req('192.0.2.11'))
    request_guard.enforce_rate_limit(req('192.0.2.12'))
    assert len(fake.counts) == 2


def test_production_without_shared_store_fails_closed(monkeypatch):
    monkeypatch.setattr(request_guard, '_get_redis', lambda: None)
    monkeypatch.setattr(request_guard.settings, 'environment', 'production')
    with pytest.raises(HTTPException) as exc:
        request_guard.enforce_rate_limit(req())
    assert exc.value.status_code == 503
