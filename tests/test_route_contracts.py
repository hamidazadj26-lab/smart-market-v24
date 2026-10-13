from app.main import app


def test_market_price_trend_route_is_unique():
    matches = [r for r in app.routes if getattr(r, "path", None) == "/api/market-prices/trend" and "GET" in getattr(r, "methods", set())]
    assert len(matches) == 1
