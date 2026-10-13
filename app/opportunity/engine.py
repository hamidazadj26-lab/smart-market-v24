"""Opportunity engine: combines matching with available market evidence."""
from .scoring import calculate
from .explanation import explain


def evaluate_opportunity(manufacturer, customer, demand, market=None, match=None, weights=None, actor_evidence=None):
    score = calculate(
        manufacturer, customer, demand,
        market=market, match=match, weights=weights,
        actor_evidence=actor_evidence,
    )
    return {'score': score, 'explanation': explain(score)}
