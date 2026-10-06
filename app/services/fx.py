"""Central, source-backed FX resolution for commercial calculations."""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models import FXRate


def _active_rate(db: Session, base: str, quote: str):
    now = datetime.now(timezone.utc)
    return db.query(FXRate).filter(
        FXRate.base_currency == base,
        FXRate.quote_currency == quote,
        FXRate.status.notin_(['Rejected', 'Expired']),
        (FXRate.expires_at.is_(None) | (FXRate.expires_at >= now)),
    ).order_by(FXRate.observed_at.desc()).first()


def resolve_fx_rate(db: Session, source_currency: str, target_currency: str):
    source = source_currency.upper().strip()
    target = target_currency.upper().strip()
    if source == target:
        return 1.0, None
    direct = _active_rate(db, source, target)
    if direct:
        return float(direct.rate), direct
    inverse = _active_rate(db, target, source)
    if inverse and float(inverse.rate) > 0:
        return 1.0 / float(inverse.rate), inverse
    raise HTTPException(
        status_code=422,
        detail=f'نرخ ارز معتبر و منبع‌دار برای {source}/{target} وجود ندارد.'
    )


def resolve_fx_map(db: Session, currencies, target_currency: str):
    target = target_currency.upper().strip()
    result = {target: 1.0}
    provenance = {}
    for currency in sorted({str(c).upper().strip() for c in currencies if c}):
        rate, row = resolve_fx_rate(db, currency, target)
        result[currency] = rate
        if row:
            provenance[currency] = {
                'fx_rate_id': row.id,
                'base_currency': row.base_currency,
                'quote_currency': row.quote_currency,
                'rate': float(row.rate),
                'observed_at': row.observed_at.isoformat() if row.observed_at else None,
                'expires_at': row.expires_at.isoformat() if row.expires_at else None,
                'confidence': float(row.confidence or 0),
                'source_id': row.source_id,
                'source_url': row.source_url,
            }
    return result, provenance
