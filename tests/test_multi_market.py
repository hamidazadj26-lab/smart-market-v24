from app.services.multi_market import market_name, DEFAULT_WEIGHTS
def test_market_profile_defaults():
    assert market_name("Iran","Oman")=="Iran → Oman"
    assert sum(DEFAULT_WEIGHTS.values())==100
