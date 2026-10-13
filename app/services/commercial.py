from math import isfinite

def calculate_offer(data):
    q=max(float(data.quantity),0.0)
    base=q*max(float(data.supplier_unit_price),0.0)
    fob_cost=base+sum(float(data.__dict__.get(k,0) or 0) for k in ('packaging_cost','inland_cost','export_cost'))
    commission=fob_cost*(float(data.commission_percent)/100.0)+float(data.commission_fixed)
    fob_cost_with_commission=fob_cost+commission
    margin_rate=float(data.target_margin_percent)/100.0
    fob_total=fob_cost_with_commission/(1-margin_rate) if margin_rate<1 else fob_cost_with_commission
    cif_cost=fob_total+float(data.freight_cost)+float(data.insurance_cost)+float(data.customs_cost)+float(data.other_cost)
    cif_unit=cif_cost/q if q else 0
    fob_unit=fob_total/q if q else 0
    estimated_profit=fob_total-fob_cost_with_commission
    profit_pct=(estimated_profit/fob_total*100) if fob_total else 0
    return {'fob_total':round(fob_total,6),'cif_total':round(cif_cost,6),'fob_unit_price':round(fob_unit,6),'cif_unit_price':round(cif_unit,6),'estimated_profit':round(estimated_profit,6),'estimated_profit_percent':round(profit_pct,4),'commission_amount':round(commission,6),'base_cost':round(base,6),'fob_cost_before_margin':round(fob_cost_with_commission,6)}

def compare_quotes(quotes):
    rows=[]
    for q in quotes:
        landed=(q.unit_price + (q.freight_cost+q.other_cost)/q.quantity) if q.quantity else q.unit_price
        rows.append({'id':q.id,'supplier_name':q.supplier_name,'currency':q.currency,'incoterm':q.incoterm,'unit_price':q.unit_price,'landed_unit_estimate':round(landed,6),'quantity':q.quantity,'lead_time_days':q.lead_time_days,'validity_days':q.validity_days,'status':q.status})
    return sorted(rows,key=lambda x:x['landed_unit_estimate'])

def deal_decision_engine(*, landed_unit_cost, benchmark_unit_price=None, target_margin_percent=10.0,
                         minimum_margin_percent=0.0, selling_commission_percent=0.0,
                         selling_commission_fixed_per_unit=0.0, quantity=1.0):
    """Return transparent price/profit scenarios; never selects a deal for the user."""
    cost=float(landed_unit_cost)
    if cost < 0:
        raise ValueError('landed_unit_cost must be >= 0')
    target=float(target_margin_percent)/100
    minimum=float(minimum_margin_percent)/100
    commission=float(selling_commission_percent)/100
    fixed=float(selling_commission_fixed_per_unit)
    if not 0 <= minimum < 1 or not 0 <= target < 1 or not 0 <= commission < 1:
        raise ValueError('margin and commission percentages must be between 0 and 100')
    if minimum > target:
        raise ValueError('minimum_margin_percent cannot exceed target_margin_percent')
    def price_for_margin(m):
        denominator=1.0-m-commission
        if denominator <= 0:
            return None
        return (cost+fixed)/denominator
    min_price=price_for_margin(minimum)
    target_price=price_for_margin(target)
    market_price=float(benchmark_unit_price) if benchmark_unit_price is not None else None
    def economics(sell):
        if sell is None: return None
        commission_amount=sell*commission+fixed
        gross=sell-cost-commission_amount
        margin=(gross/sell*100) if sell else 0.0
        return {'sell_unit_price':round(sell,6),'commission_per_unit':round(commission_amount,6),'profit_per_unit':round(gross,6),'margin_percent':round(margin,4)}
    out={
        'landed_unit_cost':round(cost,6),'benchmark_unit_price':round(market_price,6) if market_price is not None else None,
        'target_margin_percent':target_margin_percent,'minimum_margin_percent':minimum_margin_percent,
        'selling_commission_percent':selling_commission_percent,'selling_commission_fixed_per_unit':fixed,
        'minimum_price_for_minimum_margin':economics(min_price),'target_price':economics(target_price),
        'market_room_per_unit':round(market_price-cost,6) if market_price is not None else None,
        'market_room_percent_of_benchmark':round((market_price-cost)/market_price*100,4) if market_price else None,
        'target_price_vs_benchmark_percent':round((target_price-market_price)/market_price*100,4) if target_price is not None and market_price else None,
        'target_margin_supported_at_benchmark': bool(market_price is not None and economics(market_price)['margin_percent'] >= minimum_margin_percent),
        'target_margin_supported_at_benchmark_exact': bool(market_price is not None and economics(market_price)['margin_percent'] >= target_margin_percent),
        'market_ceiling':economics(market_price) if market_price is not None else None,
        'quantity':float(quantity),
    }
    if market_price is not None and market_price > 0:
        out['market_total_value']=round(market_price*float(quantity),6)
    if target_price is not None:
        out['target_total_value']=round(target_price*float(quantity),6)
        out['target_profit_total']=round((economics(target_price)['profit_per_unit'])*float(quantity),6)
    return out
