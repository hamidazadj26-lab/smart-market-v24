from __future__ import annotations
import asyncio
import json
from typing import Any
import httpx

class DivarError(RuntimeError):
    pass

class DivarAdapter:
    """Official Divar Open Platform Finder adapter.

    Uses the SEARCH_POST capability when a Divar API key is configured.
    It does not attempt to bypass login, CAPTCHA, rate limits, or access controls.
    """
    endpoint = "https://open-api.divar.ir/v2/open-platform/finder/post"

    def __init__(self, api_key: str, timeout: float = 15.0, max_retries: int = 2):
        if not api_key:
            raise DivarError("Divar API Key تنظیم نشده است.")
        self.api_key = api_key
        self.timeout = max(1.0, min(float(timeout), 60.0))
        self.max_retries = max(0, min(int(max_retries), 3))

    async def search(self, query_text: str, *, city: str | None = None, category: str | None = None, limit: int = 20) -> dict[str, Any]:
        query_text = (query_text or "").strip()
        if not query_text:
            raise DivarError("عبارت جستجوی دیوار نمی‌تواند خالی باشد.")
        body: dict[str, Any] = {"query_text": query_text}
        if city:
            body["city"] = city.strip()
        if category:
            body["category"] = category.strip()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(
                        self.endpoint,
                        headers={"Content-Type": "application/json", "x-api-key": self.api_key},
                        json=body,
                    )
                except httpx.TimeoutException as exc:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.25 * (2 ** attempt)); continue
                    raise DivarError("مهلت پاسخ دیوار تمام شد.") from exc
                except httpx.HTTPError as exc:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.25 * (2 ** attempt)); continue
                    raise DivarError("ارتباط با API دیوار برقرار نشد.") from exc
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.25 * (2 ** attempt)); continue
                    raise DivarError(f"API دیوار خطای HTTP {response.status_code} داد.")
                if response.status_code >= 400:
                    raise DivarError(f"API دیوار خطای HTTP {response.status_code} داد.")
                try:
                    payload = response.json()
                except (ValueError, json.JSONDecodeError) as exc:
                    raise DivarError("پاسخ API دیوار قابل پردازش نیست.") from exc
                if not isinstance(payload, dict):
                    raise DivarError("ساختار پاسخ API دیوار نامعتبر است.")
                return payload
        raise DivarError("خطای ناشناخته API دیوار")


def normalize_posts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw = payload.get("posts") or payload.get("results") or payload.get("data") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        post_id = item.get("token") or item.get("id") or item.get("post_token")
        title = item.get("title") or item.get("name")
        description = item.get("description") or item.get("desc") or ""
        url = item.get("url") or (f"https://divar.ir/v/{post_id}" if post_id else None)
        if not title and not description and not post_id:
            continue
        out.append({"id": post_id, "title": title, "description": description, "url": url, "raw": item})
    return out
