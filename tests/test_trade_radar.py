from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import DiscoveryCandidate, SourceSignal
from app.services.trade_radar import build_trade_radar, _score, _unit


def make_db():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_score_renormalizes_only_over_observed_dimensions():
    out = _score([(0.5, 0.8), (0.5, None)])
    assert out == {'score': 80.0, 'coverage_pct': 50.0}
    assert _score([(1, None)]) == {'score': None, 'coverage_pct': 0.0}


def test_unit_handles_fraction_percent_and_invalid_values():
    assert _unit(0.8) == 0.8
    assert _unit(80) == 0.8
    assert _unit(float('nan')) is None
    assert _unit(-1) == 0.0


def test_trade_radar_ranks_candidates_without_claiming_verified_buyer():
    db = make_db()
    sig = SourceSignal(raw_text='Buyer looking for epoxy resin', source_url='https://example.org/buy', source_title='Public purchase notice', confidence=0.8, observed_at=datetime.now(timezone.utc))
    db.add(sig); db.flush()
    c = DiscoveryCandidate(name='Example Trading', country='Afghanistan', city='Herat', product_name='Epoxy resin', candidate_type='Potential Customer', demand_likelihood=0.8, confidence=0.75, trust_score=0.7, evidence={'text':'public notice'}, source_url='https://example.org/buy', source_title='Public purchase notice', source_signal_id=sig.id, status='Review')
    db.add(c); db.commit()
    out = build_trade_radar(db, market='Afghanistan', limit=10)
    assert out['status'] == 'ok'
    assert out['candidate_count'] == 1
    item = out['discovery_candidates'][0]
    assert item['name'] == 'Example Trading'
    assert item['score'] is not None
    assert item['source_url'] == 'https://example.org/buy'
    assert 'Manually verify' in item['next_action']
    assert any('not verified buyers' in x for x in out['guardrails'])
    db.close()


def test_trade_radar_empty_database_is_safe():
    db = make_db()
    out = build_trade_radar(db, limit=10)
    assert out['opportunity_count'] == 0
    assert out['candidate_count'] == 0
    assert out['opportunities'] == []
    assert out['discovery_candidates'] == []
    db.close()
