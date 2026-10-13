from app.discovery.connectors import get_connector
from app.discovery.sources import platform_connector, resolve_sources


def test_explicit_platform_connectors_exist():
    assert get_connector("divar").mode == "official_api_or_public_web"
    assert get_connector("buskool").domains == ("buskool.com",)
    assert get_connector("tender").domains == ("irantender.com",)


def test_tender_alias_resolves_to_same_connector():
    assert get_connector("iran_tender").key == "tender"
    assert get_connector("تندر").key == "tender"
    assert platform_connector("tender").label == "ایران تندر"


def test_platform_sources_are_domain_restricted():
    sources = {x.key: x for x in resolve_sources(["divar", "buskool", "tender"])}
    assert sources["divar"].domains == ("divar.ir",)
    assert sources["buskool"].domains == ("buskool.com",)
    assert sources["tender"].domains == ("irantender.com",)


def test_connector_aliases_and_fallbacks():
    assert get_connector("باسکول").key == "buskool"
    assert get_connector("ایران تندر").key == "tender"
    assert get_connector("divar.ir").fallback_channel == "firecrawl"
    assert get_connector("divar").requires_api_key is True


def test_platform_queries_are_domain_restricted_and_semantic():
    from app.discovery.sources import build_queries, resolve_sources
    for key in ("divar", "buskool", "tender"):
        src = resolve_sources([key])[0]
        q = build_queries("PET preform", "Afghanistan", ["buyer"], src)[0]
        assert "PET preform" in q
        assert "Afghanistan" in q
        if key != "divar":
            assert "site:" in q
            assert src.domains[0] in q
