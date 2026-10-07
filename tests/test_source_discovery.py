from app.discovery.source_discovery import extract_domains, score_domain, register_discovered
from app.models import Source


def test_extract_domains_from_public_results():
    items=[{'url':'https://supplier.example.com/page'},{'url':'https://google.com/search'},{'url':'https://factory-example.org/a'}]
    assert extract_domains(items)==['supplier.example.com','factory-example.org']


def test_score_domain_rewards_commercial_terms():
    score, reason=score_domain('industrial-supplier.example.com', product='HDPE', market='Afghanistan')
    assert score > 0.5
    assert 'commercial source vocabulary' in reason


def test_register_discovered_marks_unverified():
    class Query:
        def filter(self, *args, **kwargs): return self
        def first(self): return None
    class DB:
        def query(self, model): return Query()
        def add(self, obj): self.obj=obj
        def flush(self): self.obj.id=1
    db=DB()
    result=register_discovered(db,['new-supplier.example'],evidence_url='https://search.example/r',product='HDPE',market='Afghanistan')
    assert result[0]['status']=='discovered_unverified'
    src=db.obj
    assert src.access_mode=='public_web'
    assert src.availability_status=='Discovered'
    assert src.configured is False
