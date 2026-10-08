from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable

# Public, commercially useful search language. These are query hints only;
# they never grant access to private/authenticated content.
GENERIC_INTENT = (
    "buyer purchase procurement RFQ request quotation wanted importer distributor wholesaler supplier",
    "خریدار خرید تامین کننده واردکننده عمده فروش استعلام قیمت درخواست خرید مناقصه",
)
DOCUMENT_INTENT = (
    "filetype:pdf RFQ tender procurement catalog price list quotation brochure",
    "filetype:pdf مناقصه استعلام خرید لیست قیمت کاتالوگ درخواست پیشنهاد",
)
SIGNAL_INTENT = (
    "new supplier announcement stock available capacity factory expansion import",
    "تامین کننده جدید موجودی ظرفیت تولید توسعه کارخانه واردات",
)
RARE_PUBLIC_INTENT = (
    "intitle:RFQ intitle:tender intitle:procurement intitle:quotation",
    "intitle:مناقصه intitle:استعلام intitle:خرید intitle:فراخوان",
)
DOCUMENT_TYPES = ("pdf", "xlsx", "xls", "csv", "doc", "docx")

SOURCE_HINTS = {
    "divar": (
        "خرید عمده فروشنده تامین کننده واردکننده قیمت",
        "buyer supplier wholesale importer price",
    ),
    "buskool": (
        "عمده فروشی خرید فروش تامین کننده واردکننده قیمت",
        "wholesale buyer supplier importer price",
    ),
    "tender": (
        "مناقصه استعلام خرید تامین کالا درخواست پیشنهاد",
        "tender procurement RFQ supplier bid",
    ),
    "tender_global": (
        "tender procurement RFQ buyer supplier contract award",
        "purchase notice request for quotation supplier",
    ),
    "manufacturer_web": (
        "factory manufacturer plant exporter importer distributor",
        "کارخانه تولیدکننده صادرکننده واردکننده توزیع کننده",
    ),
}


def _clean(value: str) -> str:
    return " ".join((value or "").split())


def _domain_scope(domains: Iterable[str]) -> str:
    return " ".join(f"site:{d}" for d in domains if d)


def _product_variants(product: str) -> list[str]:
    """Generate conservative lexical variants; no semantic invention."""
    product = _clean(product)
    if not product:
        return []
    variants = [product, f'"{product}"']
    # Preserve the original term and add a compact token form for engines that
    # perform poorly on quoted multi-word product names.
    compact = re.sub(r"[^\w\u0600-\u06ff.-]+", " ", product).strip()
    if compact and compact not in variants:
        variants.append(compact)
    return variants[:3]


def build_deep_queries(
    product: str,
    market: str,
    terms: Iterable[str],
    source_key: str,
    domains: Iterable[str] = (),
    *,
    max_queries: int = 12,
) -> list[str]:
    """Build a diversified portfolio of public/indexable commercial queries.

    The planner deliberately targets hard-to-find *public* evidence: procurement
    notices, indexed documents, supplier announcements, capacity signals and
    role-specific pages. It never creates instructions to bypass authentication,
    CAPTCHA, paywalls, robots restrictions or other access controls.
    """
    product = _clean(product)
    market = _clean(market)
    user_terms = _clean(" ".join(x for x in terms if _clean(x)))
    scope = "" if source_key == "divar" else _domain_scope(domains)
    hints = SOURCE_HINTS.get(source_key, ())
    variants = _product_variants(product) or [product]
    current_year = datetime.now(timezone.utc).year

    families: list[list[str]] = []
    # 1) User intent and exact product/market searches.
    families.append([
        f"{variants[0]} {market} {user_terms}".strip(),
        f"{variants[0]} {market} {GENERIC_INTENT[0]}".strip(),
        f"{variants[min(1, len(variants)-1)]} {market} {GENERIC_INTENT[1]}".strip(),
    ])
    # 2) Documents and structured commercial evidence.
    families.append([
        f"{product} {market} {DOCUMENT_INTENT[0]}",
        f"{product} {market} {DOCUMENT_INTENT[1]}",
        f"{product} {market} {SIGNAL_INTENT[0]}",
        f"{product} {market} {SIGNAL_INTENT[1]}",
    ])
    # 3) Low-visibility indexed pages: titles, URLs and recent material.
    families.append([f"{product} {market} {RARE_PUBLIC_INTENT[0]}"])
    families.append([f"{product} {market} after:{current_year - 1} procurement supplier buyer"])
    families.append([f"{product} {market} {RARE_PUBLIC_INTENT[1]}"])
    # 4) Source-specific commercial vocabulary.
    if hints:
        families.append([f"{product} {market} {hint} {user_terms}".strip() for hint in hints])
    # 5) Structured document extensions. Keep only a small sample so the query
    # budget remains useful across different evidence families.
    families.append([f"{product} {market} filetype:{ext} procurement supplier buyer" for ext in DOCUMENT_TYPES[:4]])

    # Round-robin the families. This prevents a large generic family from
    # consuming the entire budget before rare-document/recent-signal queries run.
    seeds: list[str] = []
    max_len = max((len(f) for f in families), default=0)
    for i in range(max_len):
        for family in families:
            if i < len(family):
                seeds.append(family[i])

    result: list[str] = []
    seen: set[str] = set()
    for raw_query in seeds:
        query = _clean(raw_query)
        if scope:
            query = f"{query} {scope}".strip()
        query = re.sub(r"(?:\s+site:[^\s]+){2,}", lambda m: " " + " ".join(m.group(0).split()), query)
        query = query[:1800]
        if query and query not in seen:
            seen.add(query)
            result.append(query)
        if len(result) >= max_queries:
            break
    return result
