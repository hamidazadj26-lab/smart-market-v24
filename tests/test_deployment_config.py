from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_env_template_documents_required_shared_redis():
    content = (ROOT / '.env.example').read_text(encoding='utf-8')
    assert 'REDIS_URL=' in content
    assert 'RATE_LIMIT_NAMESPACE=' in content
    assert 'Required in production' in content


def test_compose_wires_shared_redis_to_app():
    content = (ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    assert 'redis:7-alpine' in content
    assert 'REDIS_URL: redis://redis:6379/0' in content
    assert 'condition: service_healthy' in content


def test_logout_route_is_rate_limited():
    content = (ROOT / 'app/routers/system.py').read_text(encoding='utf-8')
    logout = content.split('@router.post("/api/logout")', 1)[1]
    assert 'enforce_rate_limit(request)' in logout.split('\n@router.', 1)[0]
