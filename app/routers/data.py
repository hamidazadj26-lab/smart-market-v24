"""Core master-data and signal API routes.

V24 migration slice: public paths and response shapes remain unchanged.
"""
import hashlib
import re

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer, Demand, Manufacturer, Opportunity, Product, Source, SourceSignal
from ..schemas import CustomerIn, DemandIn, ManufacturerIn, ProductIn, SignalIn, SourceIn
from ..services.core import ALIASES, get_or_create_product
from ..services.request_guard import auth, serialize

router = APIRouter(tags=["data"])


@router.get("/api/dashboard")
def dashboard(request: Request, db=Depends(get_db)):
    auth(request, db)
    return {
        k: db.query(v).filter(getattr(v, "is_archived", False) == False).count()
        if hasattr(v, "is_archived") else db.query(v).count()
        for k, v in [
            ("manufacturers", Manufacturer), ("customers", Customer),
            ("demands", Demand), ("signals", SourceSignal),
            ("opportunities", Opportunity),
            ("products", Product),
        ]
    }


@router.get("/api/sources")
def sources(request: Request, db=Depends(get_db)):
    auth(request, db)
    return [serialize(x) for x in db.query(Source).all()]


@router.post("/api/sources")
def create_source(data: SourceIn, request: Request, db=Depends(get_db)):
    auth(request, db)
    x = Source(**data.model_dump())
    db.add(x); db.commit(); db.refresh(x)
    return serialize(x)


@router.get("/api/products")
def products(request: Request, db=Depends(get_db)):
    auth(request, db)
    return [serialize(x) for x in db.query(Product).order_by(Product.name).all()]


@router.post("/api/products")
def create_product(data: ProductIn, request: Request, db=Depends(get_db)):
    auth(request, db)
    x = get_or_create_product(db, data.name)
    x.category = data.category; x.sub_category = data.sub_category
    x.unit = data.unit; x.aliases = data.aliases; x.specifications = data.specifications
    db.commit()
    return serialize(x)


@router.get("/api/manufacturers")
def manufacturers(request: Request, db=Depends(get_db)):
    auth(request, db)
    return [serialize(x) for x in db.query(Manufacturer).filter(Manufacturer.is_archived == False).all()]


@router.post("/api/manufacturers")
def create_manufacturer(data: ManufacturerIn, request: Request, db=Depends(get_db)):
    auth(request, db)
    x = Manufacturer(**data.model_dump())
    db.add(x); db.commit(); db.refresh(x)
    return serialize(x)


@router.get("/api/customers")
def customers(request: Request, db: Session = Depends(get_db)):
    auth(request, db)
    return [serialize(x) for x in db.query(Customer).filter(Customer.is_archived == False).all()]


@router.post("/api/customers")
def create_customer(data: CustomerIn, request: Request, db: Session = Depends(get_db)):
    auth(request, db)
    x = Customer(**data.model_dump())
    db.add(x); db.commit(); db.refresh(x)
    return serialize(x)


@router.get("/api/demands")
def demands(request: Request, db=Depends(get_db)):
    auth(request, db)
    return [serialize(x) for x in db.query(Demand).filter(Demand.is_archived == False).order_by(Demand.created_at.desc()).all()]


@router.post("/api/demands")
def create_demand(data: DemandIn, request: Request, db=Depends(get_db)):
    auth(request, db)
    x = Demand(**data.model_dump())
    db.add(x); db.commit(); db.refresh(x)
    return serialize(x)


@router.get("/api/signals")
def signals(request: Request, db=Depends(get_db)):
    auth(request, db)
    return [serialize(x) for x in db.query(SourceSignal).order_by(SourceSignal.created_at.desc()).all()]


def normalize_signal_payload(raw_text: str, db):
    text = " ".join(raw_text.strip().split())
    product = None
    for alias, norm in {**ALIASES, "پودر شوینده": "detergent", "شوینده": "detergent"}.items():
        if alias.lower() in text.lower():
            product = norm
            break
    qty = None; unit = None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(میلیون|هزار|kg|کیلوگرم|تن|ton|tons|عدد|pcs|قطعه)", text, re.I)
    if m:
        qty = float(m.group(1).replace(",", ".")); unit = m.group(2).lower()
        if unit == "میلیون": qty *= 1_000_000; unit = "pcs"
        elif unit == "هزار": qty *= 1000; unit = "pcs"
        elif unit in ("kg", "کیلوگرم"): unit = "kg"
        elif unit in ("تن", "ton", "tons"): qty *= 1000; unit = "kg"
        elif unit in ("عدد", "قطعه"): unit = "pcs"
    cities = ["کابل", "هرات", "قندهار", "مزار شریف", "مزارشریف", "جلال‌آباد", "جلال اباد", "بلخ", "ننگرهار"]
    city = next((c for c in cities if c in text), None)
    return {
        "normalized_product": product, "quantity": qty, "unit": unit,
        "country": "Afghanistan" if any(x in text.lower() for x in ["afghanistan", "افغانستان", "کابل", "هرات", "قندهار", "مزار"]) else None,
        "city": city, "raw_text": text,
    }


@router.post("/api/signals")
def create_signal(data: SignalIn, request: Request, db=Depends(get_db)):
    auth(request, db)
    payload = normalize_signal_payload(data.raw_text, db)
    payload.update(data.normalized_payload or {})
    content_hash = hashlib.sha256((data.raw_text.strip().lower() + "|" + (data.source_url or "")).encode("utf-8")).hexdigest()
    existing = db.query(SourceSignal).filter(SourceSignal.content_hash == content_hash).first()
    if existing:
        return {**serialize(existing), "deduplicated": True}
    x = SourceSignal(**{**data.model_dump(exclude={"normalized_payload"}), "normalized_payload": payload, "content_hash": content_hash})
    db.add(x); db.commit(); db.refresh(x)
    return {**serialize(x), "deduplicated": False}
