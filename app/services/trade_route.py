from __future__ import annotations

VALID_STATUSES={'Unverified','Partially Verified','Verified','Rejected'}

def _n(v): return max(float(v or 0),0.0)

def convert_amount(amount, source_currency, target_currency, fx_rates):
    amount=_n(amount)
    if source_currency==target_currency: return amount
    rates=fx_rates or {}
    rate=rates.get(source_currency)
    if rate is None: raise ValueError(f'Explicit FX rate is required for {source_currency} -> {target_currency}')
    target_rate=rates.get(target_currency,1.0)
    if rate<=0 or target_rate<=0: raise ValueError('FX rates must be > 0')
    return amount*rate/target_rate

def calculate_trade_route(segments, quantity, currency='USD', fx_rates=None):
    if _n(quantity)<=0: raise ValueError('quantity must be > 0')
    totals={'freight':0.0,'border':0.0,'transit':0.0,'destination_handling':0.0,'other':0.0}
    distance=0.0; days=0.0; currencies=set()
    for s in segments:
        sc=s.get('currency',currency); currencies.add(sc)
        for key, field in [('freight','freight_cost'),('border','border_cost'),('transit','transit_cost'),('destination_handling','destination_handling'),('other','other_cost')]:
            totals[key]+=convert_amount(s.get(field,0),sc,currency,fx_rates)
        distance+=_n(s.get('distance_km')); days+=_n(s.get('transit_days'))
    total=sum(totals.values())
    return {'status':'Calculated','currency':currency,'quantity':float(quantity),**{f'{k}_total':round(v,6) for k,v in totals.items()},'total_route_cost':round(total,6),'route_unit_cost':round(total/quantity,6),'distance_km':round(distance,3),'transit_days':round(days,3),'assumptions':{'explicit_fx_required':len(currencies)>1 or (currencies and next(iter(currencies))!=currency),'segments_count':len(segments),'costs_are_explicit':True}}
