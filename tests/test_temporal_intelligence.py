from datetime import datetime, timezone, timedelta
from app.services.temporal_intelligence import trend, freshness

def test_trend_rising():
    x=trend([10,11,12])
    assert x['direction']=='Rising' and x['change_pct']==20.0

def test_trend_falling():
    assert trend([12,11,10])['direction']=='Falling'

def test_freshness_decays():
    now=datetime.now(timezone.utc)
    assert freshness(now,30,now)==1.0
    assert 0.45 < freshness(now-timedelta(days=30),30,now) < 0.55
