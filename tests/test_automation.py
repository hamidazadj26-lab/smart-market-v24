from datetime import datetime, timezone, timedelta
from app.models import Opportunity
from app.services.automation import build_automation_plan


def make_op(**kw):
    base=dict(id=1, opportunity_stage='Qualified', is_archived=False,
              stage_due_at=datetime.now(timezone.utc)-timedelta(hours=2),
              stage_updated_at=datetime.now(timezone.utc)-timedelta(days=4),
              next_action='پیگیری RFQ', lost_reason=None)
    base.update(kw)
    return Opportunity(**base)

class FakeQ:
    def __init__(self, rows): self.rows=rows
    def filter(self,*a,**k): return self
    def all(self): return self.rows
    def first(self): return self.rows[0] if self.rows else None

class FakeDB:
    def query(self, model):
        name=getattr(model,'__name__','')
        if name=='OpportunityAction':
            return FakeQ([])
        return FakeQ([])

def test_overdue_and_next_action_plan():
    items=build_automation_plan(FakeDB(),make_op())
    markers={x['marker'] for x in items}
    assert 'OVERDUE' in markers
    assert 'NEXT' in markers

def test_terminal_has_no_plan():
    items=build_automation_plan(FakeDB(),make_op(opportunity_stage='Won'))
    assert items==[]

def test_due24_plan():
    op=make_op(stage_due_at=datetime.now(timezone.utc)+timedelta(hours=5), next_action=None)
    items=build_automation_plan(FakeDB(),op)
    assert any(x['marker']=='DUE24' for x in items)
