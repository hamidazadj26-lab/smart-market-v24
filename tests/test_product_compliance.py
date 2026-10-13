from app.services.product_compliance import compliance_gate

def test_no_classification_blocks_gate():
    class Q:
        def filter(self,*a): return self
        def order_by(self,*a): return self
        def all(self): return []
    class DB:
        def query(self,*a): return Q()
    class P: id=1; name='Epoxy Resin'
    class M: id=2; name='Iran → Afghanistan'
    r=compliance_gate(DB(),P(),M())
    assert r['status']=='Blocked' and 'hs_classification' in r['blockers']

def test_migration_exists():
    from pathlib import Path
    p=Path(__file__).parents[1]/'migrations/versions/0018_product_compliance.py'
    assert p.exists() and 'product_compliance' in p.read_text()
