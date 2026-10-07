from app.discovery.sources import build_queries, normalize_domain, resolve_sources

def test_normalize_domain_accepts_urls_and_rejects_invalid_values():
    assert normalize_domain('https://www.example.com/path') == 'www.example.com'
    assert normalize_domain('bad domain') is None
    assert normalize_domain('example') is None

def test_resolve_sources_supports_named_platforms_and_custom_domains():
    sources=resolve_sources(['web','divar','site:example.org'],['https://example.net/path'])
    keys={x.key for x in sources}
    assert {'web','divar','site:example.org','custom'} <= keys
    assert next(x for x in sources if x.key=='divar').domains==('divar.ir',)
    assert next(x for x in sources if x.key=='custom').domains==('example.net',)

def test_build_queries_is_domain_scoped():
    source=next(x for x in resolve_sources(['divar']) if x.key=='divar')
    query=build_queries('PET preform','Afghanistan',['buyer','importer'],source)[0]
    assert 'PET preform' in query and 'site:' not in query and 'buyer importer' in query


def test_required_platform_sources_are_explicit_and_scoped():
    sources=resolve_sources(["buskool", "tender", "divar"])
    assert next(x for x in sources if x.key=="buskool").domains == ("buskool.com",)
    assert next(x for x in sources if x.key=="tender").domains == ("irantender.com",)
    assert next(x for x in sources if x.key=="divar").channel == "divar"

def test_divar_api_query_does_not_include_web_site_operator():
    source=next(x for x in resolve_sources(["divar"]) if x.key=="divar")
    query=build_queries("PET preform","Afghanistan",["buyer"],source)[0]
    assert "site:" not in query
