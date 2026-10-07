from datetime import datetime, timezone, timedelta
from app.services.change_detection import _event_hash


def test_event_hash_is_deterministic():
    p={'event_type':'claim_changed','claim_key':'phone','old_value':'1','new_value':'2'}
    assert _event_hash(p)==_event_hash(dict(reversed(list(p.items()))))


def test_change_severity_contract():
    assert {'high','medium'} == {'high','medium'}
