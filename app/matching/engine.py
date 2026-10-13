"""Core matching engine.

The engine coordinates eligibility, evidence-aware scoring and explanation.
Persistence remains outside this module.
"""
from .eligibility import eligible
from .scoring import calculate
from .explanation import build


def match(manufacturer, customer, demand, weights=None, actor_evidence=None):
    is_eligible = eligible(manufacturer, customer, demand)
    if not is_eligible:
        return None
    score = calculate(manufacturer, customer, demand, weights, actor_evidence=actor_evidence)
    return {
        'score': score,
        'explanation': build(
            score,
            eligible=True,
            evidence_status=getattr(demand, 'verification_status', 'Unverified'),
        ),
    }
