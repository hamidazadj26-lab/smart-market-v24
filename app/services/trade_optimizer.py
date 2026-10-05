from __future__ import annotations
from itertools import product
from .trade_route import convert_amount
from .import_cost import calculate_import_cost


def _n(v):
    return max(float(v or 0), 0.0)


def optimize_trade_scenarios(*, quotes, routes, quantity, target_currency='USD', fx_rates=None,
                              import_rules=None, customs_values=None, limit=100):
    q=_n(quantity)
    if q <= 0:
        raise ValueError('quantity must be > 0')
    if not quotes:
        raise ValueError('at least one supplier quote is required')
    if not routes:
        raise ValueError('at least one trade route is required')
    fx_rates=fx_rates or {}
    import_rules=import_rules or {}
    customs_values=customs_values or {}
    rows=[]
    for quote, route in product(quotes, routes):
        key=f"{quote.id}:{route.id}"
        supplier_currency=quote.currency
        goods_total=convert_amount(_n(quote.unit_price)*q, supplier_currency, target_currency, fx_rates)
        supplier_other=convert_amount(_n(quote.other_cost), supplier_currency, target_currency, fx_rates)
        route_result=route.get('calculation') if isinstance(route, dict) else route.calculation
        route_cost=route_result['total_route_cost']
        route_currency=route_result['currency']
        if route_currency != target_currency:
            route_cost=convert_amount(route_cost, route_currency, target_currency, fx_rates)
        import_total=0.0
        import_detail=None
        rule=import_rules.get(key) or import_rules.get(str(route.id))
        cv=customs_values.get(key)
        if cv is not None:
            if not rule:
                rows.append({'status':'Needs Verification','key':key,'supplier_quote_id':quote.id,'route_id':route.id,
                             'reason':'Explicit customs value was supplied but no current verified import-cost rule is available.'})
                continue
            imp=calculate_import_cost(rule, float(cv), quantity=q)
            import_total=convert_amount(imp['total_import_taxes_and_fees'], rule.currency, target_currency, fx_rates)
            import_detail={**imp,'normalized_import_taxes_and_fees':round(import_total,6),'target_currency':target_currency}
        total=goods_total+supplier_other+route_cost+import_total
        rows.append({
            'status':'Calculated','key':key,'supplier_quote_id':quote.id,'supplier_name':quote.supplier_name,
            'route_id':route.id,'route_name':route.name,'incoterm':quote.incoterm,'quantity':q,
            'target_currency':target_currency,'supplier_goods_total':round(goods_total,6),
            'supplier_other_cost':round(supplier_other,6),'route_cost':round(route_cost,6),
            'import_taxes_and_fees':round(import_total,6),'total_trade_cost':round(total,6),
            'trade_unit_cost':round(total/q,6),'route_distance_km':route_result['distance_km'],
            'route_transit_days':route_result['transit_days'],'lead_time_days':quote.lead_time_days,
            'supplier_quote_status':quote.status,'route_verification_status':route.verification_status,
            'import_cost':import_detail,
            'assumptions':{
                'supplier_freight_excluded_when_route_selected':True,
                'supplier_freight_not_added':True,
                'route_cost_includes_route_segments':True,
                'import_cost_added_only_with_explicit_customs_value_and_verified_rule':True,
                'no_implicit_fx':True,
            }
        })
    valid=[r for r in rows if r.get('status')=='Calculated']
    valid.sort(key=lambda x:(x['trade_unit_cost'], x['route_transit_days'], x['route_distance_km']))
    return {'quantity':q,'target_currency':target_currency,'scenario_count':len(valid),'skipped_count':len(rows)-len(valid),'scenarios':valid[:max(1,min(limit,500))]}
