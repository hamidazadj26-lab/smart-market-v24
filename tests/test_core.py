from app.services.core import normalize_product, haversine

def test_normalize(): assert normalize_product('  رزین اپوکسی ')=='epoxy resin'
def test_distance(): assert 110 < haversine(35.7,51.4,36.3,59.6) < 800
