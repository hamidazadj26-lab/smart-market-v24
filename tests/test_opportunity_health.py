from types import SimpleNamespace
from app.services.opportunity_health import calculate_opportunity_health

class Q:
    def filter(self,*a,**k): return self
    def count(self): return 0

class DB:
    def get(self, cls, ident): return SimpleNamespace(phone=None,email=None,website=None) if cls.__name__ in {'Customer','Manufacturer'} else SimpleNamespace()
    def query(self, cls): return Q()

def test_health_explains_missing_evidence():
    op=SimpleNamespace(id=1, customer_id=1, manufacturer_id=2, demand_id=None, product_id=3, verification_status='Unverified', opportunity_stage='Discovered', stage_updated_at=None, stage_due_at=None, next_action='پیگیری')
    out=calculate_opportunity_health(DB(),op)
    assert out['label'] in {'Watch','At Risk'}
    assert out['risk_index'] >= 0
    assert any('Demand' in x for x in out['reasons'])

def test_health_closed_is_closed():
    op=SimpleNamespace(id=2, customer_id=1, manufacturer_id=2, demand_id=3, product_id=3, verification_status='Verified', opportunity_stage='Won', stage_updated_at=None, stage_due_at=None, next_action='')
    out=calculate_opportunity_health(DB(),op)
    assert out['label']=='Closed'
