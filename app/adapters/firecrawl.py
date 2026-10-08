from __future__ import annotations
from typing import Any
import asyncio
import json
import httpx

class FirecrawlError(RuntimeError):
    pass

class FirecrawlAdapter:
    """Bounded adapter for Firecrawl public web search; never bypasses site restrictions."""
    def __init__(self, api_key: str, timeout: float = 15.0, max_retries: int = 2):
        if not api_key:
            raise FirecrawlError("Firecrawl API Key تنظیم نشده است.")
        self.api_key = api_key
        self.timeout = max(1.0, min(float(timeout), 60.0))
        self.max_retries = max(0, min(int(max_retries), 3))

    async def search(self, query: str, *, limit: int = 20, scrape_markdown: bool = True) -> dict[str, Any]:
        query = (query or "").strip()
        if not query:
            raise FirecrawlError("عبارت جستجو نمی‌تواند خالی باشد.")
        url = "https://api.firecrawl.dev/v2/search"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body: dict[str, Any] = {
            "query": query,
            "limit": max(1, min(int(limit), 50)),
            "sources": [{"type": "web"}],
        }
        if scrape_markdown:
            body["scrapeOptions"] = {"formats": ["markdown"], "onlyMainContent": True}
        last_error = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(url, headers=headers, json=body)
                except httpx.TimeoutException as exc:
                    last_error = "مهلت جستجوی Firecrawl تمام شد."
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.25 * (2 ** attempt)); continue
                    raise FirecrawlError(last_error) from exc
                except httpx.HTTPError as exc:
                    last_error = "ارتباط با Firecrawl برقرار نشد."
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.25 * (2 ** attempt)); continue
                    raise FirecrawlError(last_error) from exc
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = f"Firecrawl خطای موقت HTTP {response.status_code} داد."
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After", "")
                        try: delay = max(0.25, min(float(retry_after), 5.0))
                        except ValueError: delay = 0.25 * (2 ** attempt)
                        await asyncio.sleep(delay); continue
                    raise FirecrawlError(last_error)
                if response.status_code >= 400:
                    raise FirecrawlError(f"Firecrawl خطای HTTP {response.status_code} داد.")
                try:
                    payload = response.json()
                except (ValueError, json.JSONDecodeError) as exc:
                    raise FirecrawlError("پاسخ Firecrawl قابل پردازش نیست.") from exc
                if not isinstance(payload, dict):
                    raise FirecrawlError("ساختار پاسخ Firecrawl نامعتبر است.")
                return payload
        raise FirecrawlError(last_error or "خطای ناشناخته Firecrawl")

def normalize_search(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict): return []
    data = payload.get("data") or payload.get("results") or []
    if not isinstance(data, list): return []
    out = []
    for item in data:
        if not isinstance(item, dict): continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        out.append({
            "url": item.get("url"),
            "title": item.get("title") or metadata.get("title"),
            "description": item.get("description") or metadata.get("description"),
            "markdown": item.get("markdown") or item.get("content"),
            "source": "firecrawl",
        })
    return out
