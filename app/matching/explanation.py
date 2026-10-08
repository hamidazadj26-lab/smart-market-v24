"""Machine-readable and human-readable matching explanations."""

def build(score, *, eligible=True, evidence_status='Unverified'):
    return {
        'eligible': bool(eligible),
        'score': score.total,
        'priority': score.priority,
        'evidence_status': evidence_status,
        'coverage': score.coverage,
        'dimensions': {
            'product_fit': score.product_fit,
            'capacity': score.capacity,
            'demand': score.demand,
            'trust': score.trust,
            'location': score.location,
            'price': score.price,
            'logistics': score.logistics,
            'evidence': score.evidence,
            'freshness': score.freshness,
            'buyer_reliability': score.buyer_reliability,
            'supplier_reliability': score.supplier_reliability,
        },
        'dimension_evidence': score.dimension_evidence,
        'distance_km': score.distance_km,
        'reasons': list(score.reasons),
        'limitations': [
            'داده‌های ناموجود به‌عنوان امتیاز واقعی تلقی نشده‌اند.',
            'امتیاز تطبیق به‌تنهایی به معنی امکان قطعی معامله نیست.',
        ],
    }
