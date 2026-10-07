from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


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
    assert "24.20.0" in sw
    assert "styles.css?v=24.20.0" in sw
    assert "app.js?v=24.20.0" in sw
    assert "styles.css?v=24.20.0" in idx
    assert "app.js?v=24.20.0" in idx


def test_repository_excludes_runtime_state_and_secrets():
    s = (ROOT / ".gitignore").read_text()
    assert "*.db" in s
    assert ".env" in s
    assert "__pycache__/" in s
