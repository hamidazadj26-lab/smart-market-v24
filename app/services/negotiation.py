from typing import Optional

def negotiation_engine(*, landed_unit_cost: float, benchmark_unit_price: Optional[float] = None,
                       target_margin_percent: float = 10.0, minimum_margin_percent: float = 0.0,
                       selling_commission_percent: float = 0.0, selling_commission_fixed_per_unit: float = 0.0,
                       opening_buffer_percent: float = 5.0, quantity: float = 1.0,
                       concession_steps: Optional[list[float]] = None):
    cost=float(landed_unit_cost); target=float(target_margin_percent)/100; minimum=float(minimum_margin_percent)/100
    commission=float(selling_commission_percent)/100; fixed=float(selling_commission_fixed_per_unit)
    buffer=float(opening_buffer_percent)/100
    if cost < 0 or quantity <= 0: raise ValueError('cost and quantity must be >= 0 and quantity > 0')
    if not 0 <= minimum < 1 or not 0 <= target < 1 or not 0 <= commission < 1: raise ValueError('invalid margin/commission')
    if minimum > target: raise ValueError('minimum margin cannot exceed target margin')
    if buffer < 0: raise ValueError('opening buffer must be >= 0')
    steps=concession_steps if concession_steps is not None else [0,2,5,8,10]
    if any(float(x)<0 or float(x)>=100 for x in steps): raise ValueError('concession steps must be 0..99.999')
    def price_for_margin(m):
        d=1-m-commission
        return None if d<=0 else (cost+fixed)/d
    def economics(sell):
        if sell is None: return None
        comm=sell*commission+fixed; profit=sell-cost-comm
        return {'unit_price':round(sell,6),'commission_per_unit':round(comm,6),'profit_per_unit':round(profit,6),'margin_percent':round((profit/sell*100) if sell else 0,4),'total_value':round(sell*quantity,6),'total_profit':round(profit*quantity,6)}
    minimum_price=price_for_margin(minimum); target_price=price_for_margin(target)
    opening_price=target_price*(1+buffer) if target_price is not None else None
    benchmark=float(benchmark_unit_price) if benchmark_unit_price is not None else None
    rows=[]
    for s in sorted(set(float(x) for x in steps)):
        p=opening_price*(1-s/100) if opening_price is not None else None
        e=economics(p)
        if e: e['concession_percent']=s; e['above_minimum_price_percent']=round((p/minimum_price-1)*100,4) if minimum_price else None; rows.append(e)
    return {
        'landed_unit_cost':round(cost,6),'benchmark_unit_price':round(benchmark,6) if benchmark is not None else None,
        'minimum_margin_percent':minimum_margin_percent,'target_margin_percent':target_margin_percent,
        'selling_commission_percent':selling_commission_percent,'selling_commission_fixed_per_unit':fixed,
        'opening_buffer_percent':opening_buffer_percent,
        'minimum_acceptable_price':economics(minimum_price),'target_price':economics(target_price),
        'opening_price':economics(opening_price),'benchmark_economics':economics(benchmark) if benchmark is not None else None,
        'concession_scenarios':rows,'quantity':float(quantity),
        'opening_vs_benchmark_percent':round((opening_price-benchmark)/benchmark*100,4) if opening_price is not None and benchmark else None,
        'minimum_vs_benchmark_percent':round((minimum_price-benchmark)/benchmark*100,4) if minimum_price is not None and benchmark else None,
        'notes':['Opening price is derived only from the explicit opening buffer.','Minimum acceptable price is formula-based and not a recommendation.','Concession scenarios are descriptive; the user decides negotiation strategy.']
    }
