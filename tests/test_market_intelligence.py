from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from app.services.market_intelligence import build_benchmark, normalize_price, compare_to_benchmark

def obs(price, days=0, confidence=.9, status='Verified', currency='USD', unit='kg'):
    return SimpleNamespace(price=price,currency=currency,unit=unit,confidence=confidence,verification_status=status,observed_at=datetime.now(timezone.utc)-timedelta(days=days))

def test_benchmark_median_and_confidence():
    r=build_benchmark([obs(10),obs(11,2),obs(9,5),obs(50,200,0.1,'Unverified')],target_currency='USD',target_unit='kg',fx_rates={'USD':1},min_effective=3)
    assert r['status']=='Benchmark'
    assert 9 <= r['weighted_median_price'] <= 11
    assert r['effective_count']==4

def test_missing_fx_is_not_guessed():
    value,err=normalize_price(100,'EUR','kg','USD','kg',fx_rates={'USD':1})
    assert value is None and err=='missing_fx'

def test_compare_band():
    b=SimpleNamespace(currency='USD',unit='kg',weighted_median_price=100,median_price=100)
    r=compare_to_benchmark(85,'USD','kg',b,fx_rates={'USD':1})
    assert r['comparable'] and r['band']=='Below Benchmark'
