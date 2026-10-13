from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any

BUY_EXPLICIT = ("rfq", "request for quotation", "request to buy", "purchase order", "procurement request", "wanted to buy", "looking to buy", "buying", "خرید", "درخواست خرید", "استعلام خرید", "سفارش خرید", "نیاز به خرید", "مناقصه")
SELL = ("for sale", "available", "we supply", "supplier", "manufacturer", "تولیدکننده", "فروش", "فروشنده", "موجود است", "عرضه")
DIRECTORY = ("directory", "company profile", "listing", "دایرکتوری", "معرفی شرکت", "پروفایل شرکت")
NEWS = ("news", "press release", "خبر", "گزارش خبری", "اخبار")
NEGATIVE = ("expired", "closed", "awarded", "sold out", "منقضی", "بسته شد", "برنده مناقصه", "فروخته شد")


def _norm(t: str) -> str:
    return " ".join((t or "").replace("ي", "ی").replace("ك", "ک").split()).lower()


def _hits(t: str, words: tuple[str, ...]) -> list[str]:
    return [w for w in words if w.lower() in t]


def evidence_classify(text: str, *, source_name: str | None = None, source_url: str | None = None,
                      requested_product: str | None = None, extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    t = _norm(text)
    extracted = extracted or {}
    buy = _hits(t, BUY_EXPLICIT)
    sell = _hits(t, SELL)
    directory = _hits(t, DIRECTORY)
    news = _hits(t, NEWS)
    negative = _hits(t, NEGATIVE)
    quantity = bool(extracted.get("quantities"))
    prices = bool(extracted.get("prices"))
    contacts = extracted.get("contacts") or {}
    contact = bool(contacts.get("emails") or contacts.get("phones") or source_url)
    product_match = bool(requested_product and _norm(requested_product) in t)
    explicit_rfq = bool(re.search(r"\brfq\b|request\s+for\s+quotation|درخواست خرید|استعلام خرید", t, re.I))

    dimensions = {
        "purchase_intent": 1.0 if buy else 0.0,
        "product_match": 1.0 if product_match else None,
        "quantity_evidence": 1.0 if quantity else 0.0,
        "price_evidence": 1.0 if prices else 0.0,
        "contact_evidence": 1.0 if contact else 0.0,
        "source_context": 0.8 if explicit_rfq else (0.4 if source_name else 0.2),
        "negative_status": 0.0 if negative else 1.0,
    }
    known = [v for v in dimensions.values() if v is not None]
    base = sum(known) / len(known) if known else 0.0
    demand = min(1.0, 0.40*dimensions["purchase_intent"] + 0.18*(dimensions["product_match"] or 0) + 0.14*dimensions["quantity_evidence"] + 0.08*dimensions["price_evidence"] + 0.08*dimensions["contact_evidence"] + 0.07*dimensions["source_context"] + 0.05*dimensions["negative_status"])
    if negative:
        demand *= 0.25
    if directory and not buy:
        demand *= 0.55
    if news and not buy:
        demand *= 0.45

    if negative:
        classification = "Expired/Closed Signal"
    elif buy and quantity and (product_match or not requested_product):
        classification = "Active Purchase Demand"
    elif buy:
        classification = "Potential Purchase Demand"
    elif sell and not buy:
        classification = "Supply Signal"
    elif directory:
        classification = "Directory/Company Profile"
    elif news:
        classification = "News/Information"
    else:
        classification = "Business Signal"

    return {
        "classification": classification,
        "demand_likelihood": round(demand, 4),
        "confidence": round(min(1.0, 0.45 + 0.55 * base), 4),
        "evidence": {
            "purchase_intent_hits": buy,
            "supply_hits": sell,
            "directory_hits": directory,
            "news_hits": news,
            "negative_status_hits": negative,
            "explicit_rfq": explicit_rfq,
            "dimensions": dimensions,
            "decision_basis": "evidence_based_v1",
        },
    }
