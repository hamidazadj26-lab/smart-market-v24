from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def _current_frontend_version():
    config = (ROOT / "app" / "config.py").read_text()
    match = re.search(r"version:\\s*str\\s*=\\s*['\\\"]([^'\\\"]+)['\\\"]", config)
    assert match, "app/config.py must declare the application version"
    return match.group(1)


def test_index_is_mobile_first_and_rtl():
    s = (STATIC / "index.html").read_text()
    assert 'lang="fa" dir="rtl"' in s
    assert 'viewport-fit=cover' in s
    assert 'width=device-width' in s


def test_mobile_navigation_contract_exists():
    s = (STATIC / "index.html").read_text()
    for key in ("home", "search", "opportunities", "market", "operations"):
        assert f'data-nav="{key}"' in s


def test_pwa_manifest_has_install_icons():
    s = (STATIC / "manifest.json").read_text()
    assert '"display":"standalone"' in s
    assert 'icon-192.png' in s and 'icon-512.png' in s
    assert (STATIC / "icons/icon-192.png").exists()
    assert (STATIC / "icons/icon-512.png").exists()


def test_service_worker_cache_matches_current_frontend_version():
    sw = (STATIC / "sw.js").read_text()
    idx = (STATIC / "index.html").read_text()
    version = _current_frontend_version()
    assert f"smart-market-v{version}" in sw
    assert f"styles.css?v={version}" in sw
    assert f"app.js?v={version}" in sw
    assert f"styles.css?v={version}" in idx
    assert f"app.js?v={version}" in idx


def test_repository_excludes_runtime_state_and_secrets():
    s = (ROOT / ".gitignore").read_text()
    assert "*.db" in s
    assert ".env" in s
    assert "__pycache__/" in s


def test_trade_radar_is_exposed_in_dashboard_and_cache_bumped():
    js = (STATIC / "app.js").read_text()
    idx = (STATIC / "index.html").read_text()
    sw = (STATIC / "sw.js").read_text()
    assert 'id="tradeRadar"' in js
    assert "tradeRadarCenter" in js
    assert "/api/intelligence/trade-radar" in js
    version = _current_frontend_version()
    assert version in idx and version in sw


def test_interactive_map_is_wired_to_authenticated_geojson_endpoint():
    js = (STATIC / "app.js").read_text()
    router = (ROOT / "app/routers/intelligence.py").read_text()
    assert 'id="intelligenceMap"' in js
    assert "intelligenceMapCenter" in js
    assert "/api/intelligence/map.geojson?" in js
    assert "@router.get('/api/intelligence/map.geojson')" in router
    assert "location_basis" in (ROOT / "app/services/intelligence_map.py").read_text()
