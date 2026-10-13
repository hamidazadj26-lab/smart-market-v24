from datetime import datetime, timezone, timedelta
from app.services.command_center import _stage_counts, _action_state

def test_stage_counts():
    class O:
        def __init__(self,s): self.opportunity_stage=s
    out=_stage_counts([O('Discovered'),O('Negotiation'),O('Won')])
    assert out['Discovered']==1 and out['Negotiation']==1 and out['Won']==1 and out['Lost']==0

def test_action_state_empty():
    assert _action_state(None, [], datetime.now(timezone.utc)) == {'open':0,'overdue':0,'due_24h':0}
