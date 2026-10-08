from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from ..models import Customer, Manufacturer, Product, SourceSignal
from .extraction import extract_contacts, extract_quantity_price, classify_intent
from .normalization import normalize_commercial_text
from .evidence import evidence_classify
from ..services.core import normalize_product, get_or_create_product

COUNTRY_ALIASES = {
    "افغانستان": "Afghanistan", "afghanistan": "Afghanistan",
    "ایران": "Iran", "iran": "Iran",
    "پاکستان": "Pakistan", "pakistan": "Pakistan",
    "عراق": "Iraq", "iraq": "Iraq",
    "ترکیه": "Turkey", "turkey": "Turkey",
}
CITY_ALIASES = {
    "کابل": "Kabul", "kabul": "Kabul", "هرات": "Herat", "herat": "Herat",
    "قندهار": "Kandahar", "kandahar": "Kandahar", "مزار شریف": "Mazar-i-Sharif",
    "مزارشریف": "Mazar-i-Sharif", "جلال‌آباد": "Jalalabad", "jalalabad": "Jalalabad",
    "تهران": "Tehran", "مشهد": "Mashhad", "اصفهان": "Isfahan",
}
BUY_WORDS = ("buy", "purchase", "procurement", "rfq", "request for quotation", "wanted", "need", "import", "خرید", "درخواست خرید", "نیاز", "استعلام", "مناقصه")
FACTORY_WORDS = ("factory", "manufacturer", "production", "plant", "تولید", "کارخانه", "صنایع", "تولیدکننده")
DISTRIBUTOR_WORDS = ("distributor", "dealer", "wholesaler", "trading", "واردات", "توزیع", "بازرگانی")

@dataclass
class ExtractedSignal:
    company_name: str | None
    country: str | None
    city: str | None
    activity_type: str | None
    product_name: str | None
    demand_likelihood: float
    customer_type: str
    confidence: float
    evidence: dict[str, Any]


def _norm_text(text: str) -> str:
    return " ".join((text or "").replace("ي", "ی").replace("ك", "ک").split())


def _contains(text: str, words: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(w.lower() in low for w in words)


def detect_country_city(text: str) -> tuple[str | None, str | None]:
    low = _norm_text(text).lower()
    country = next((v for k, v in COUNTRY_ALIASES.items() if k.lower() in low), None)
    city = next((v for k, v in CITY_ALIASES.items() if k.lower() in low), None)
    if not country and city in {"Kabul", "Herat", "Kandahar", "Mazar-i-Sharif", "Jalalabad"}:
        country = "Afghanistan"
    return country, city


def extract_company_name(text: str, fallback: str | None = None) -> str | None:
    text = _norm_text(text)
    patterns = [
        r"(?:company|co\.?|ltd\.?|limited|corp\.?|inc\.?)[\s:,-]+([A-Za-z][A-Za-z0-9& .'-]{2,100})",
        r"(?:شرکت|کمپانی)[\s:،-]+([^،\n;|]{3,100})",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            candidate = m.group(1).strip(" .,-")
            if candidate:
                return candidate[:250]
    return fallback.strip() if fallback else None


def detect_product(text: str, requested_product: str | None = None) -> str | None:
    text_low = _norm_text(text).lower()
    if requested_product and requested_product.lower() in text_low:
        return normalize_product(requested_product)
    known = {
        "رزین اپوکسی": "epoxy resin", "epoxy resin": "epoxy resin",
        "چسب بتن": "concrete adhesive", "concrete adhesive": "concrete adhesive",
        "مواد شوینده": "detergent", "detergent": "detergent",
        "هیومیک اسید": "humic acid", "humic acid": "humic acid",
        "سیمان": "cement", "cement": "cement",
        "pet preform": "pet preform", "پریفورم پت": "pet preform",
        "masterbatch": "masterbatch", "مستربچ": "masterbatch",
    }
    for key, value in known.items():
        if key.lower() in text_low:
            return value
    return normalize_product(requested_product) if requested_product else None


def classify_signal(text: str, *, source_name: str | None = None, requested_product: str | None = None, place: dict[str, Any] | None = None) -> ExtractedSignal:
    text = _norm_text(text)
    country, city = detect_country_city(text)
    product = detect_product(text, requested_product)
    contacts = extract_contacts(text, (place or {}).get("website") or (place or {}).get("maps_url"))
    commercial = extract_quantity_price(text)
    normalized = normalize_commercial_text(text, source_url=(place or {}).get("website"), source_title=source_name)
    evidence_result = evidence_classify(text, source_name=source_name, source_url=(place or {}).get("website"), requested_product=requested_product, extracted=normalized)
    classification = evidence_result["classification"]
    activity = {
        "Active Purchase Demand": "buyer / procurement",
        "Potential Purchase Demand": "buyer / procurement",
        "Supply Signal": "supplier / seller",
        "Directory/Company Profile": "business / company",
        "News/Information": "information / news",
        "Expired/Closed Signal": "closed / expired",
    }.get(classification, "business / company")
    if classification in {"Active Purchase Demand", "Potential Purchase Demand"}:
        customer_type = classification
    elif classification == "Supply Signal":
        customer_type = "Potential Supplier"
    else:
        customer_type = "Potential Customer"
    evidence = {
        **evidence_result["evidence"],
        "contacts": contacts,
        "commercial": commercial,
        "intent": classify_intent(text),
        "normalized_commercial": normalized,
        "source_name": source_name,
    }
    confidence = evidence_result["confidence"]
    if contacts["emails"] or contacts["phones"]: confidence = min(1.0, confidence + 0.05)
    return ExtractedSignal(company_name=extract_company_name(text, (place or {}).get("name")), country=country or (place or {}).get("country"), city=city or (place or {}).get("city"), activity_type=activity, product_name=product, demand_likelihood=evidence_result["demand_likelihood"], customer_type=customer_type, confidence=confidence, evidence=evidence)


def similarity(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _norm_text(a).lower(), _norm_text(b).lower()).ratio()


def find_duplicate_customer(db: Session, name: str, country: str | None, city: str | None) -> Customer | None:
    candidates = db.query(Customer).filter(Customer.is_archived == False).all()
    for c in candidates:
        if country and c.country and c.country.lower() != country.lower():
            continue
        if city and c.city and c.city.lower() != city.lower():
            continue
        if similarity(c.name, name) >= 0.88:
            return c
    return None


def upsert_customer_from_signal(db: Session, signal: ExtractedSignal, source_signal: SourceSignal, place: dict[str, Any] | None = None) -> Customer | None:
    if not signal.company_name or not signal.country:
        return None
    product = get_or_create_product(db, signal.product_name) if signal.product_name else None
    existing = find_duplicate_customer(db, signal.company_name, signal.country, signal.city)
    if existing:
        if product and not existing.product_id:
            existing.product_id = product.id
        existing.confidence = max(existing.confidence or 0, signal.confidence)
        return existing
    p = place or {}
    customer = Customer(
        name=signal.company_name,
        country=signal.country,
        city=signal.city,
        address=p.get("address"), latitude=p.get("latitude"), longitude=p.get("longitude"),
        activity_type=signal.activity_type, product_id=product.id if product else None,
        phone=p.get("phone"), website=p.get("website"), source_id=source_signal.source_id,
        source_url=source_signal.source_url or p.get("maps_url"), source_title=source_signal.source_title,
        retrieved_at=datetime.now(timezone.utc), verification_status="Unverified", confidence=signal.confidence,
    )
    db.add(customer)
    return customer


def discover_from_signal(db: Session, source_signal: SourceSignal, requested_product: str | None = None, place: dict[str, Any] | None = None) -> dict[str, Any]:
    extracted = classify_signal(source_signal.raw_text, source_name=source_signal.source_title, requested_product=requested_product, place=place)
    customer = upsert_customer_from_signal(db, extracted, source_signal, place=place)
    if customer:
        source_signal.normalized_payload = {
            **(source_signal.normalized_payload or {}),
            "discovery": {
                "customer_type": extracted.customer_type,
                "activity_type": extracted.activity_type,
                "demand_likelihood": extracted.demand_likelihood,
                "confidence": extracted.confidence,
                "evidence": extracted.evidence,
            },
        }
    db.commit()
    return {"classification": extracted.customer_type, "customer_id": customer.id if customer else None, "extracted": extracted.__dict__}


def parse_demand(text: str, requested_product: str | None = None) -> dict[str, Any]:
    """Deterministic first-pass demand parser; uncertain fields remain None."""
    t = _norm_text(text)
    product = detect_product(t, requested_product)
    qty = None; unit = None
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(million|میلیون|thousand|هزار|kg|kgs|کیلوگرم|ton|tons|تن|pcs|pieces|عدد|قطعه)', t, re.I)
    if m:
        qty = float(m.group(1).replace(',', '.'))
        u = m.group(2).lower()
        if u in ('million','میلیون'): qty, unit = qty * 1_000_000, 'pcs'
        elif u in ('thousand','هزار'): qty, unit = qty * 1000, 'pcs'
        elif u in ('kg','kgs','کیلوگرم'): unit = 'kg'
        elif u in ('ton','tons','تن'): qty, unit = qty * 1000, 'kg'
        else: unit = 'pcs'
    urgency = None
    low = t.lower()
    if any(x in low for x in ('urgent','immediately','asap','فوری','سریع','فورا')): urgency = 'urgent'
    elif any(x in low for x in ('this month','monthly','ماهانه','این ماه')): urgency = 'monthly'
    country, city = detect_country_city(t)
    buy = _contains(t, BUY_WORDS)
    components={'base_context':0.25,'product':0.25 if product else 0.0,'purchase_intent':0.20 if buy else 0.0,'quantity':0.15 if qty else 0.0,'country':0.10 if country else 0.0,'city':0.05 if city else 0.0}
    confidence=min(sum(components.values()),1.0)
    return {'product': product, 'quantity': qty, 'unit': unit, 'country': country, 'city': city, 'urgency': urgency, 'is_demand_signal': buy and bool(product), 'confidence': confidence, 'confidence_components':components, 'evidence':{'purchase_intent':buy,'product_match':bool(product),'quantity_present':bool(qty),'country_present':bool(country),'city_present':bool(city)}}
