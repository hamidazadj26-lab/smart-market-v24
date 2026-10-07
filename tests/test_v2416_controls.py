from app.discovery.engine import parse_demand
from app.services.discovery_controls import consume_request, DiscoveryBudgetExceeded
from app.services.job_queue import create_job
from app.models import DiscoveryUsage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base

class S:
    discovery_global_requests_per_minute=10
    discovery_source_requests_per_minute=3
    discovery_user_requests_per_minute=5

def db_session():
    e=create_engine('sqlite:///:memory:', connect_args={'check_same_thread':False})
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, expire_on_commit=False)()

def test_demand_confidence_is_decomposable():
    d=parse_demand('Buyer needs 500 tons HDPE for Afghanistan this month', 'HDPE')
    assert d['is_demand_signal'] is True
    assert 'confidence_components' in d
    assert sum(d['confidence_components'].values()) == d['confidence']

def test_central_budget_applies_source_and_job_limits():
    db=db_session(); job=create_job(db,'external_discovery',{},max_requests=2); db.commit()
    consume_request(db,job,source_key='web',user_id=1,settings=S())
    consume_request(db,job,source_key='web',user_id=1,settings=S())
    try:
        consume_request(db,job,source_key='web',user_id=1,settings=S())
        assert False
    except DiscoveryBudgetExceeded:
        pass
    assert job.requests_used == 2
    assert db.query(DiscoveryUsage).count() == 3
