from app.schemas.schemas import ExternalDiscoveryIn
from app.discovery.sources import resolve_sources, build_queries


def test_external_discovery_accepts_query_terms_and_domains():
    data = ExternalDiscoveryIn(product="PET preform", market="Iran → Afghanistan", sources=["divar"], query_terms=["buyer", "importer"], domains=["example.com"])
    assert data.query_terms == ["buyer", "importer"]
    assert data.domains == ["example.com"]


def test_multiple_sources_are_domain_scoped_without_duplicates():
    sources = resolve_sources(["divar", "site:example.com"], ["example.org"])
    queries = [build_queries("PET preform", "Afghanistan", ["buyer"], s)[0] for s in sources]
    assert any('PET preform Afghanistan buyer' in q and 'site:' not in q for q in queries)
    assert any("site:example.com" in q for q in queries)
    assert any("site:example.org" in q for q in queries)


def test_deep_query_planner_surfaces_multiple_public_signal_types():
    from app.discovery.sources import build_queries, resolve_sources
    src = resolve_sources(["tender"])[0]
    queries = build_queries("PET preform", "Afghanistan", ["buyer"], src)
    assert len(queries) >= 5
    joined = "\n".join(queries).lower()
    assert "filetype:pdf" in joined
    assert "rfq" in joined or "استعلام" in joined
    assert "site:irantender.com" in joined


def test_deep_query_planner_is_domain_scoped_for_buskool():
    from app.discovery.sources import build_queries, resolve_sources
    src = resolve_sources(["buskool"])[0]
    queries = build_queries("industrial detergent", "Afghanistan", ["supplier"], src)
    assert queries
    assert all("site:buskool.com" in q for q in queries)


def test_deep_query_planner_never_adds_private_access_instructions():
    from app.discovery.sources import build_queries, resolve_sources
    src = resolve_sources(["web"])[0]
    queries = build_queries("PET preform", "Afghanistan", [], src)
    joined = " ".join(queries).lower()
    assert "password" not in joined
    assert "login" not in joined
    assert "captcha bypass" not in joined


def test_deep_search_targets_low_visibility_public_documents_and_fresh_signals():
    from app.discovery.sources import build_queries, resolve_sources
    src = resolve_sources(["buskool"])[0]
    queries = build_queries("PET preform", "Afghanistan", ["buyer"], src)
    joined = "\n".join(queries).lower()
    assert "filetype:pdf" in joined
    assert "intitle:" in joined
    assert "after:" in joined
    assert all("site:buskool.com" in q for q in queries)


def test_deep_search_never_generates_private_access_or_bypass_terms():
    from app.discovery.deep_search import build_deep_queries
    queries = build_deep_queries("PET preform", "Afghanistan", [], "web")
    joined = " ".join(queries).lower()
    forbidden = ("password", "captcha bypass", "bypass login", "private account", "paywall bypass")
    assert not any(x in joined for x in forbidden)
