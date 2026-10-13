import pytest
from app.adapters.osiris import _safe_base_url, _items, ALLOWED_FEEDS


def test_osiris_base_url_is_restricted_to_official_https_host():
    assert _safe_base_url('https://osirisai.live/') == 'https://osirisai.live'
    with pytest.raises(ValueError):
        _safe_base_url('http://osirisai.live')
    with pytest.raises(ValueError):
        _safe_base_url('https://example.com')


def test_osiris_feed_allowlist_prevents_arbitrary_paths():
    assert set(ALLOWED_FEEDS) == {'country_risk', 'maritime', 'gdelt'}


def test_osiris_payload_normalization_only_extracts_record_lists():
    assert _items({'items': [{'id': 1}]}) == [{'id': 1}]
    assert _items([{'id': 2}]) == [{'id': 2}]
    assert _items({'count': 5, 'metadata': {'status': 'ok'}}) == []
    assert _items({'count': 5}) == []
