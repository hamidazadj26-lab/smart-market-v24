from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from app.services.source_evidence import freshness_score, _domain, _claim


def test_freshness_decay():
    now = datetime.now(timezone.utc)
    assert freshness_score(now) > freshness_score(now - timedelta(days=60))


def test_domain_normalization():
    assert _domain('https://www.example.com/a') == 'example.com'


def test_claim_prefers_details():
    ev = SimpleNamespace(details={'claim_key':'phone','claim_value':'+93700'}, evidence_type='contact', excerpt='other')
    assert _claim(ev) == ('phone', '93700')
