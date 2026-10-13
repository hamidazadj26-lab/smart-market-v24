"""Read-only, opt-in adapter for selected public OSIRIS intelligence feeds.

OSIRIS outputs are contextual intelligence only: they are never promoted to
buyer evidence, verified demand, logistics quotations, or customs rules.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx

ALLOWED_FEEDS = {
    "country_risk": "/api/country-risk",
    "maritime": "/api/maritime",
    "gdelt": "/api/gdelt",
}


def _safe_base_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"osirisai.live", "www.osirisai.live"}:
        raise ValueError("OSIRIS base URL must use the official HTTPS host osirisai.live")
    return value.rstrip("/")


def _items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "features", "countries", "vessels", "events"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


async def _fetch_one(client: httpx.AsyncClient, name: str, path: str) -> dict:
    try:
        response = await client.get(path)
        response.raise_for_status()
        payload = response.json()
        items = _items(payload)
        return {
            "feed": name,
            "status": "available",
            "http_status": response.status_code,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "item_count": len(items),
            "items": items[:25],
            "truncated": len(items) > 25,
            "role": "context_only_not_commercial_evidence",
        }
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {
            "feed": name,
            "status": "unavailable",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "item_count": 0,
            "items": [],
            "error_type": type(exc).__name__,
            "role": "context_only_not_commercial_evidence",
        }


async def fetch_osiris_context(*, base_url: str, timeout_seconds: float = 4.0, feeds=None) -> dict:
    """Fetch only allow-listed public feeds; failures degrade independently."""
    base = _safe_base_url(base_url)
    selected = list(feeds or ("country_risk", "maritime", "gdelt"))
    unknown = set(selected) - set(ALLOWED_FEEDS)
    if unknown:
        raise ValueError("Unsupported OSIRIS feed requested")
    timeout = httpx.Timeout(max(0.5, min(float(timeout_seconds), 8.0)))
    async with httpx.AsyncClient(base_url=base, timeout=timeout, follow_redirects=False, headers={"Accept": "application/json", "User-Agent": "SmartMarket-OSIRIS-Adapter/1.0"}) as client:
        results = await asyncio.gather(*[_fetch_one(client, name, ALLOWED_FEEDS[name]) for name in selected])
    return {
        "provider": "OSIRIS",
        "status": "available" if any(x["status"] == "available" for x in results) else "unavailable",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "feeds": results,
        "guardrails": [
            "OSIRIS records are contextual signals, not proof of a buyer or purchase demand.",
            "No data is written to Smart Market by this read-only endpoint.",
            "Feed payloads are external and untrusted; verify before making a commercial decision.",
        ],
    }
