from datetime import datetime, timezone, timedelta
from app.services.trade_rules import rule_is_current

class R:
    status='Verified'; effective_from=None; effective_to=None

def test_current_rule():
    assert rule_is_current(R())

def test_future_rule_not_current():
    r=R(); r.effective_from=datetime.now(timezone.utc)+timedelta(days=1)
    assert not rule_is_current(r)

def test_expired_status_not_current():
    r=R(); r.status='Expired'
    assert not rule_is_current(r)
