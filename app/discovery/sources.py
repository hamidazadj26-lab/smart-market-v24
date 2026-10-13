from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .connectors import get_connector, PLATFORM_CONNECTORS
from .deep_search import build_deep_queries

@dataclass(frozen=True)
class DiscoverySource:
    key: str
    label: str
    channel: str
    domains: tuple[str, ...] = ()
    description: str = ""
    access_mode: str = "public_web"
    capability: str = "indexed_public_search"
    requires_api_key: bool = False
    fallback_channel: str | None = None
    limitations: tuple[str, ...] = ()

BUILTIN_SOURCES: tuple[DiscoverySource, ...] = (
    DiscoverySource("web", "وب عمومی", "firecrawl", description="جستجوی وب عمومی با صفحات نمایه‌شده", access_mode="public_web", capability="indexed_public_search"),
    DiscoverySource("places", "Google Places", "google_places", description="شرکت‌ها و مکان‌های تجاری از Google Places", access_mode="official_api", capability="places_search", requires_api_key=True),
    DiscoverySource("divar", "دیوار", "divar", ("divar.ir",), "API رسمی دیوار در صورت وجود کلید؛ در غیر این صورت fallback به وب عمومی نمایه‌شده.", access_mode="official_api", capability="search_posts", requires_api_key=True, fallback_channel="firecrawl", limitations=("کلید API برای مسیر رسمی لازم است.",)),
    DiscoverySource("buskool", "باسکول", "firecrawl", ("buskool.com",), "فقط جستجوی صفحات عمومی و نمایه‌شده باسکول.", access_mode="public_web", capability="indexed_public_search", limitations=("API رسمی در این نسخه پیکربندی نشده است.", "دسترسی خصوصی انجام نمی‌شود.")),
    DiscoverySource("tender", "ایران تندر", "firecrawl", ("irantender.com",), "فقط جستجوی صفحات عمومی و نمایه‌شده ایران تندر.", access_mode="public_web", capability="indexed_public_search", limitations=("API رسمی در این نسخه پیکربندی نشده است.",)),
    DiscoverySource("tender_global", "تندر جهانی", "firecrawl", ("tenderint.com",), "فقط جستجوی صفحات عمومی و نمایه‌شده تندر جهانی.", access_mode="public_web", capability="indexed_public_search", limitations=("API رسمی در این نسخه پیکربندی نشده است.",)),
    DiscoverySource("facebook", "Facebook", "firecrawl", ("facebook.com",), "جستجوی صفحات عمومی و نمایه‌شده؛ دسترسی خصوصی انجام نمی‌شود.", access_mode="public_web", capability="indexed_public_search"),
    DiscoverySource("instagram", "Instagram", "firecrawl", ("instagram.com",), "جستجوی صفحات عمومی و نمایه‌شده؛ دسترسی خصوصی انجام نمی‌شود.", access_mode="public_web", capability="indexed_public_search"),
    DiscoverySource("linkedin", "LinkedIn", "firecrawl", ("linkedin.com",), "جستجوی صفحات عمومی و نمایه‌شده؛ دسترسی خصوصی انجام نمی‌شود.", access_mode="public_web", capability="indexed_public_search"),
    DiscoverySource("manufacturer_web", "سایت تولیدکنندگان", "firecrawl", description="جستجوی عمومی سایت‌های تولیدکننده، تأمین‌کننده و واردکننده"),
    DiscoverySource("custom", "دامنه سفارشی", "firecrawl", description="جستجوی دامنه‌ای که کاربر تعیین می‌کند"),
)


def platform_connector(key: str):
    """Return the explicit connector policy for a supported platform."""
    return get_connector(key)


def normalize_domain(value: str) -> str | None:
    value=(value or "").strip().lower()
    value=re.sub(r"^https?://", "", value).split("/",1)[0].split("?",1)[0].strip(".")
    if not value or len(value)>253 or "." not in value: return None
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value): return None
    return value

def resolve_sources(source_keys: Iterable[str], domains: Iterable[str]=()) -> list[DiscoverySource]:
    catalog={s.key:s for s in BUILTIN_SOURCES}; catalog.update({"iran_tender": catalog["tender"], "تندر": catalog["tender"]}); result=[]; seen=set()
    for raw in source_keys:
        key=(raw or "").strip().lower()
        if not key: continue
        if key.startswith("site:"):
            domain=normalize_domain(key[5:])
            if not domain: continue
            src=DiscoverySource(f"site:{domain}",domain,"firecrawl",(domain,),"دامنه سفارشی", access_mode="public_web", capability="indexed_public_search")
        elif key in catalog: src=catalog[key]
        else:
            domain=normalize_domain(key)
            if not domain: continue
            src=DiscoverySource(f"site:{domain}",domain,"firecrawl",(domain,),"دامنه سفارشی", access_mode="public_web", capability="indexed_public_search")
        ident=(src.key,src.domains)
        if ident not in seen: result.append(src); seen.add(ident)
    custom=[]
    for raw in domains:
        domain=normalize_domain(raw)
        if domain and domain not in custom: custom.append(domain)
    if custom:
        src=DiscoverySource("custom","دامنه سفارشی","firecrawl",tuple(custom),"دامنه‌های تعیین‌شده در درخواست", access_mode="public_web", capability="indexed_public_search")
        ident=(src.key,src.domains)
        if ident not in seen: result.append(src)
    return result

def build_queries(product: str, market: str, query_terms: Iterable[str], source: DiscoverySource) -> list[str]:
    """Build a small portfolio of public-web discovery queries.

    Multiple query intents improve recall for hard-to-find but publicly indexed
    commercial signals such as RFQs, tender PDFs, catalogues, price lists and
    supplier announcements. Access controls are never bypassed.
    """
    return build_deep_queries(
        product,
        market,
        query_terms,
        source.key,
        source.domains,
        max_queries=8,
    )
