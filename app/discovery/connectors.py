from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformConnector:
    key: str
    label: str
    channel: str
    domains: tuple[str, ...]
    access_mode: str
    capability: str
    requires_api_key: bool = False
    fallback_channel: str | None = None
    query_hint: str = ""
    limitations: tuple[str, ...] = ()

    @property
    def mode(self) -> str:
        """Backward-compatible alias retained for existing integrations."""
        if self.fallback_channel:
            return "official_api_or_public_web" if self.access_mode == "official_api" and self.fallback_channel == "firecrawl" else f"{self.access_mode}_or_{self.fallback_channel}"
        return self.access_mode


PLATFORM_CONNECTORS: tuple[PlatformConnector, ...] = (
    PlatformConnector(
        "divar", "دیوار", "divar", ("divar.ir",),
        "official_api", "search_posts", True, "firecrawl",
        "آگهی خرید فروش تامین کالا",
        ("API رسمی فقط با کلید معتبر؛ در نبود کلید، مسیر fallback وب عمومی است.",),
    ),
    PlatformConnector(
        "buskool", "باسکول", "firecrawl", ("buskool.com",),
        "public_web", "indexed_public_search", False, None,
        "خرید فروش عمده تامین کننده واردکننده",
        ("API رسمی در این نسخه پیکربندی نشده است.", "دسترسی خصوصی یا حساب کاربری انجام نمی‌شود."),
    ),
    PlatformConnector(
        "tender", "ایران تندر", "firecrawl", ("irantender.com",),
        "public_web", "indexed_public_search", False, None,
        "مناقصه استعلام خرید فراخوان",
        ("API رسمی در این نسخه پیکربندی نشده است.", "فقط محتوای عمومی و نمایه‌شده بررسی می‌شود."),
    ),
    PlatformConnector(
        "tender_global", "تندر جهانی", "firecrawl", ("tenderint.com",),
        "public_web", "indexed_public_search", False, None,
        "tender procurement RFQ",
        ("API رسمی در این نسخه پیکربندی نشده است.", "فقط محتوای عمومی و نمایه‌شده بررسی می‌شود."),
    ),
)

_ALIASES = {
    "iran_tender": "tender", "تندر": "tender", "ایران تندر": "tender",
    "divar.ir": "divar", "باسکول": "buskool", "buskool.com": "buskool",
}

def get_connector(key: str) -> PlatformConnector | None:
    key = (key or "").strip().lower()
    key = _ALIASES.get(key, key)
    return next((x for x in PLATFORM_CONNECTORS if x.key == key), None)
