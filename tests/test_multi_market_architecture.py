from app.services.multi_market import parse_market_name, market_name

def test_parse_market_name():
    assert parse_market_name('Iran → Afghanistan') == ('Iran', 'Afghanistan')

def test_parse_invalid_market():
    assert parse_market_name(None) is None
    assert parse_market_name('Iran') is None

def test_market_name_roundtrip():
    assert market_name(' Iran ', ' Afghanistan ') == 'Iran → Afghanistan'
