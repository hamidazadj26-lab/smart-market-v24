from datetime import datetime, timezone, timedelta
from app.services.freshness import evaluate_freshness

def test_unknown_without_temporal_evidence():
    r=evaluate_freshness()
    assert r.status=='Unknown' and r.score is None

def test_expired_explicit_date():
    now=datetime(2026,1,15,tzinfo=timezone.utc)
    r=evaluate_freshness(expires_at=now-timedelta(days=1), now=now)
    assert r.status=='Expired' and r.score==0

def test_recent_signal():
    now=datetime(2026,1,15,tzinfo=timezone.utc)
    r=evaluate_freshness(published_at=now-timedelta(days=2), now=now, policy='purchase_demand')
    assert r.status=='Fresh' and r.score is not None and r.score>0.8

def test_stale_signal():
    now=datetime(2026,1,15,tzinfo=timezone.utc)
    r=evaluate_freshness(published_at=now-timedelta(days=100), now=now, policy='purchase_demand')
    assert r.status=='Stale' and r.score==0
