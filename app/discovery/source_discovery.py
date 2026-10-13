from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from ..models import Source
from .sources import normalize_domain

@dataclass(frozen=True)
class DiscoveredSource:
    domain: str
    score: float
    reason: str
    evidence_url: str | None = None

_DISCOVERY_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
_EXCLUDED = {"google.com", "googleusercontent.com", "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "twitter.com", "x.com"}


def extract_domains(items: list[dict], *, excluded: set[str] | None = None) -> list[str]:
    excluded = set(excluded or ()) | _EXCLUDED
    found: dict[str, str | None] = {}
    for item in items:
        url = item.get("url") if isinstance(item, dict) else None
        if not url:
            continue
        try:
            host = normalize_domain(urlparse(url).netloc)
        except Exception:
            host = None
        if not host or host in excluded:
            continue
        found.setdefault(host, url)
    return list(found)


def score_domain(domain: str, *, product: str = "", market: str = "", evidence_text: str = "") -> tuple[float, str]:
    score = 0.35
    reasons = ["public search result"]
    text=(evidence_text or '').lower()
    d = domain.lower()
    if any(x in d for x in ("tender", "procurement", "rfq", "purchase", "supplier", "trading", "factory", "manufacturer")):
        score += 0.25; reasons.append("commercial source vocabulary")
    if product and any(tok.lower() in d for tok in re.findall(r"[\w\u0600-\u06ff]+", product)[:2]):
        score += 0.10; reasons.append("product-related domain")
    if market and any(tok.lower() in d for tok in re.findall(r"[\w\u0600-\u06ff]+", market)[:2]):
        score += 0.05; reasons.append("market-related domain")
    return min(score, 1.0), "; ".join(reasons)


def register_discovered(db: Session, domains: list[str], *, evidence_url: str | None = None, product: str = "", market: str = "") -> list[dict]:
    results = []
    for domain in domains:
        score, reason = score_domain(domain, product=product, market=market)
        src = db.query(Source).filter(Source.base_url == f"https://{domain}").first()
        if not src:
            src = Source(
                source_type="discovered_public_web",
                name=domain,
                base_url=f"https://{domain}",
                access_mode="public_web",
                capability="indexed_public_search",
                configured=False,
                authenticated=False,
                availability_status="Discovered",
                limitations=["Discovered from public search; not independently verified.", "No private/authenticated access is attempted."],
            )
            db.add(src); db.flush()
        src.discovery_status = "discovered_unverified"
        src.discovery_score = score
        src.discovered_from_url = evidence_url
        src.discovery_evidence = {"reason": reason, "product": product, "market": market}
        results.append({"domain": domain, "source_id": src.id, "score": score, "status": src.discovery_status, "reason": reason})
    return results
