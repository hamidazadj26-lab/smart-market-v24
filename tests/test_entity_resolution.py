from app.services.entity_resolution import normalize_text, normalize_phone, normalize_domain, score_pair
from app.models import Customer

def test_normalization_handles_persian_and_identity_values():
    assert normalize_text('  شرکت كاویان  ') == 'شرکت کاویان'
    assert normalize_phone('+98 (912) ۱۲۳-۴۵۶۷') == '989121234567'
    assert normalize_domain('https://www.Example.COM/path') == 'example.com'

def test_exact_identity_signals_produce_strong_score():
    a=Customer(name='Kavian Trading', country='Iran', phone='09121234567', website='https://kavian.example')
    b=Customer(name='Kavian Trading', country='Iran', phone='09121234567', website='https://kavian.example')
    score,reasons=score_pair(a,b)
    assert score >= 80
    assert 'exact_normalized_name' in reasons
    assert 'exact_phone' in reasons
    assert 'exact_domain' in reasons

def test_different_identity_does_not_auto_match():
    a=Customer(name='Alpha Industrial', country='Iran', phone='09120000001', website='https://alpha.example')
    b=Customer(name='Beta Industrial', country='Afghanistan', phone='09330000002', website='https://beta.example')
    score,reasons=score_pair(a,b)
    assert score < 45
