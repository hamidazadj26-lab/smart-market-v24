"""Eligibility checks for candidate matching.

These checks are intentionally conservative and preserve the legacy candidate
population rules. Hard business exclusions can be added here later.
"""

def eligible(manufacturer, customer, demand) -> bool:
    if getattr(manufacturer, 'is_archived', False) or getattr(customer, 'is_archived', False) or getattr(demand, 'is_archived', False):
        return False
    if manufacturer.product_id != demand.product_id:
        return False
    if customer.product_id != demand.product_id:
        return False
    if customer.country != demand.country:
        return False
    return True
