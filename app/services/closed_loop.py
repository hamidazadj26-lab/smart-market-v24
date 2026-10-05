from __future__ import annotations
from datetime import datetime, timezone
from statistics import mean
from sqlalchemy.orm import Session
from ..models import Transaction, TradeOutcomeFeedback, Opportunity


def _now():
    return datetime.now(timezone.utc)


def _ratio(actual, agreed):
    if actual is None or agreed in (None, 0):
        return None
    return (float(actual) - float(agreed)) / float(agreed) * 100.0


def _score_success(tx: Transaction) -> float:
    outcome = tx.outcome or {}
    if tx.status == 'Completed' and outcome.get('dispute') is not True and outcome.get('cancelled') is not True:
        return 1.0
    if tx.status == 'Disputed':
        return 0.0
    return 0.5


def record_trade_feedback(db: Session, tx: Transaction, *, admin_id: int | None = None):
    """Create a structured, auditable feedback row from a completed trade.

    Unknown values stay NULL; the loop never invents missing commercial facts.
    """
    opp = db.get(Opportunity, tx.opportunity_id)
    price_delta = _ratio(tx.actual_unit_price, tx.agreed_unit_price)
    freight_delta = None
    outcome = tx.outcome or {}
    agreed_freight = outcome.get('agreed_freight')
    if tx.actual_freight is not None and agreed_freight not in (None, 0):
        freight_delta = _ratio(tx.actual_freight, agreed_freight)

    existing = db.query(TradeOutcomeFeedback).filter(TradeOutcomeFeedback.transaction_id == tx.id).first()
    if existing:
        row = existing
    else:
        row = TradeOutcomeFeedback(transaction_id=tx.id, opportunity_id=tx.opportunity_id,
                                   product_id=tx.product_id, customer_id=tx.customer_id,
                                   manufacturer_id=tx.manufacturer_id, created_by=admin_id)
        db.add(row)

    row.success_score = _score_success(tx)
    row.actual_price_delta_pct = price_delta
    row.actual_freight_delta_pct = freight_delta
    row.delivery_days = tx.actual_delivery_days
    row.quantity_variance_pct = _ratio(tx.actual_quantity, tx.quantity)
    row.feedback = {
        'payment_status': tx.payment_status,
        'logistics_status': tx.logistics_status,
        'outcome': outcome,
        'source': 'completed_transaction',
    }
    row.observed_at = _now()
    return row


def summarize_actor(db: Session, *, customer_id: int | None = None, manufacturer_id: int | None = None):
    q = db.query(TradeOutcomeFeedback)
    if customer_id is not None:
        q = q.filter(TradeOutcomeFeedback.customer_id == customer_id)
    if manufacturer_id is not None:
        q = q.filter(TradeOutcomeFeedback.manufacturer_id == manufacturer_id)
    rows = q.order_by(TradeOutcomeFeedback.observed_at.desc()).limit(500).all()
    scores = [r.success_score for r in rows if r.success_score is not None]
    delivery = [r.delivery_days for r in rows if r.delivery_days is not None]
    price = [r.actual_price_delta_pct for r in rows if r.actual_price_delta_pct is not None]
    return {
        'feedback_count': len(rows),
        'reliability_score': round(mean(scores), 4) if scores else None,
        'average_delivery_days': round(mean(delivery), 2) if delivery else None,
        'average_actual_price_delta_pct': round(mean(price), 2) if price else None,
        'evidence_status': 'Observed' if rows else 'Unknown',
    }
