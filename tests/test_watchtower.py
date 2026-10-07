from app.services.watchtower import _hash, _alert

class O:
    id=7
    is_archived=False
    opportunity_stage='Qualified'

def test_watchtower_hash_deterministic():
    assert _hash({'b':2,'a':1}) == _hash({'a':1,'b':2})

def test_alert_contract():
    x=_alert('high','source_change_high','msg','reason',O(),{'count':2})
    assert x['opportunity_id']==7
    assert x['severity']=='high'
    assert len(x['dedup_key'])==64
