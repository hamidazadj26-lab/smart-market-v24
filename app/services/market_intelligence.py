from __future__ import annotations
from datetime import datetime, timezone
from statistics import median
from math import isfinite


def _n(v, default=0.0):
    try:
        x=float(v if v is not None else default)
        return x if isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _percentile(values, p):
    if not values: return 0.0
    xs=sorted(values)
    if len(xs)==1: return xs[0]
    pos=(len(xs)-1)*p
    lo=int(pos); hi=min(lo+1,len(xs)-1); frac=pos-lo
    return xs[lo]+(xs[hi]-xs[lo])*frac


def _recency_weight(observed_at, now=None, half_life_days=30):
    now=now or datetime.now(timezone.utc)
    if observed_at is None: return 0.25
    if observed_at.tzinfo is None: observed_at=observed_at.replace(tzinfo=timezone.utc)
    age=max(0.0,(now-observed_at).total_seconds()/86400)
    return 0.5 ** (age/max(half_life_days,1))


def normalize_price(price, currency, unit, target_currency='USD', target_unit=None, fx_rates=None, unit_factors=None):
    """Convert an observation to target currency/unit. Never guesses a missing FX or unit factor."""
    fx_rates=fx_rates or {target_currency:1.0}
    unit_factors=unit_factors or {}
    if currency not in fx_rates or target_currency not in fx_rates:
        return None, 'missing_fx'
    value=_n(price)
    # fx map means source currency -> target_currency.
    value*=fx_rates[currency]/fx_rates[target_currency]
    if target_unit and unit != target_unit:
        factor=unit_factors.get((unit,target_unit))
        if factor is None: return None, 'missing_unit_conversion'
        value*=factor
    return value, None


def build_benchmark(observations, *, target_currency='USD', target_unit=None, fx_rates=None, unit_factors=None, min_effective=3):
    normalized=[]; now=datetime.now(timezone.utc)
    for o in observations:
        value,err=normalize_price(o.price,o.currency,o.unit,target_currency,target_unit,fx_rates,unit_factors)
        if value is None or value<=0: continue
        source_conf=max(0.0,min(1.0,_n(getattr(o,'confidence',0))))
        verification={'Verified':1.0,'Partially Verified':0.75,'Unverified':0.45,'Rejected':0.0}.get(getattr(o,'verification_status','Unverified'),0.45)
        rec=_recency_weight(getattr(o,'observed_at',None),now)
        weight=max(0.01, source_conf*0.55+verification*0.25+rec*0.20)
        normalized.append((value,weight,o))
    vals=[x[0] for x in normalized]
    if not vals:
        return {'status':'Insufficient Data','observation_count':len(observations),'effective_count':0,'currency':target_currency,'unit':target_unit,'confidence':0.0}
    vals_sorted=sorted(vals)
    weights=sum(x[1] for x in normalized)
    # weighted median
    acc=0.0; wm=vals_sorted[len(vals_sorted)//2]
    for v,w,o in sorted(normalized,key=lambda x:x[0]):
        acc+=w
        if acc>=weights/2: wm=v; break
    med=median(vals)
    dispersion=((max(vals)-min(vals))/med*100) if med else 0.0
    avg_conf=sum(x[1] for x in normalized)/len(normalized)
    evidence_factor=min(1.0,len(normalized)/6)
    confidence=max(0.0,min(1.0,avg_conf*0.7+evidence_factor*0.3))
    status='Benchmark' if len(normalized)>=min_effective else 'Low Evidence'
    return {
      'status':status,'observation_count':len(observations),'effective_count':len(vals),
      'low_price':min(vals),'p25_price':_percentile(vals,.25),'median_price':med,
      'p75_price':_percentile(vals,.75),'high_price':max(vals),'weighted_median_price':wm,
      'dispersion_pct':dispersion,'confidence':confidence,'currency':target_currency,'unit':target_unit or getattr(observations[0],'unit',None),
      'as_of':now,'assumptions':{'recency_half_life_days':30,'normalization':'FX and explicit unit factors only; no inferred rates'}
    }


def compare_to_benchmark(price, currency, unit, benchmark, *, fx_rates=None, unit_factors=None):
    normalized,err=normalize_price(price,currency,unit,benchmark.currency,benchmark.unit,fx_rates,unit_factors)
    if normalized is None:
        return {'comparable':False,'reason':err}
    center=benchmark.weighted_median_price or benchmark.median_price
    if center<=0:
        return {'comparable':False,'reason':'benchmark_unavailable'}
    delta_pct=(normalized-center)/center*100
    if delta_pct <= -10: band='Below Benchmark'
    elif delta_pct >= 10: band='Above Benchmark'
    else: band='Near Benchmark'
    return {'comparable':True,'normalized_price':round(normalized,8),'benchmark_price':round(center,8),'delta_pct':round(delta_pct,2),'band':band}


def build_price_trend(observations, *, target_currency='USD', target_unit=None, fx_rates=None, unit_factors=None, bucket_days=7):
    """Build chronological bucketed price points using explicit normalization only."""
    points=[]
    for o in observations:
        value, err=normalize_price(o.price,o.currency,o.unit,target_currency,target_unit,fx_rates,unit_factors)
        if value is None or value<=0 or getattr(o,'observed_at',None) is None:
            continue
        dt=o.observed_at
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        points.append((dt,value,max(0.0,min(1.0,_n(getattr(o,'confidence',0))))))
    if not points:
        return []
    points.sort(key=lambda x:x[0])
    groups={}
    for dt,value,conf in points:
        ts=int(dt.timestamp())
        bucket=int(ts//(bucket_days*86400))*(bucket_days*86400)
        groups.setdefault(bucket,[]).append((value,conf))
    out=[]
    for bucket,items in sorted(groups.items()):
        vals=[x[0] for x in items]
        weights=[max(0.05,x[1]) for x in items]
        total=sum(weights)
        weighted=sum(v*w for v,w in zip(vals,weights))/total
        out.append({'date':datetime.fromtimestamp(bucket,tz=timezone.utc).isoformat(),'count':len(vals),'low':min(vals),'median':median(vals),'high':max(vals),'weighted_average':weighted})
    return out


def source_diversity(observations, source_trust_scores=None):
    """Summarize independent sources and optionally incorporate SourceTrust scores."""
    source_trust_scores=source_trust_scores or {}
    ids=[]; urls=[]; titles=[]
    for o in observations:
        if getattr(o,'source_id',None) is not None: ids.append(o.source_id)
        elif getattr(o,'source_url',None): urls.append(o.source_url)
        elif getattr(o,'source_title',None): titles.append(o.source_title)
    unique_sources=len(set(ids)) + len(set(urls)) + len(set(titles))
    trusted=[source_trust_scores.get(i) for i in set(ids) if i in source_trust_scores]
    avg_trust=sum(trusted)/len(trusted) if trusted else None
    return {'unique_sources':unique_sources,'source_ids':len(set(ids)),'unique_urls':len(set(urls)),'trusted_sources':len(trusted),'average_source_trust':avg_trust}


def compare_supplier_quote_to_market(quote, benchmark, *, target_currency='USD', target_unit=None, fx_rates=None, unit_factors=None):
    """Compare supplier unit economics with a market benchmark using explicit conversions only."""
    fx_rates = fx_rates or {}
    unit_factors = unit_factors or {}
    unit = getattr(quote, 'unit', None) or target_unit
    base_unit_price, err = normalize_price(float(getattr(quote, 'unit_price', 0) or 0), getattr(quote, 'currency', None), unit, target_currency, target_unit, fx_rates, unit_factors)
    if base_unit_price is None:
        return {'quote_id': quote.id, 'comparable': False, 'reason': err or 'conversion_unavailable'}
    qty = float(getattr(quote, 'quantity', 0) or 0)
    extra_total = float(getattr(quote, 'freight_cost', 0) or 0) + float(getattr(quote, 'other_cost', 0) or 0)
    extra_unit = 0.0
    if extra_total and qty > 0:
        extra_unit, err = normalize_price(extra_total / qty, quote.currency, unit, target_currency, target_unit, fx_rates, unit_factors)
        if extra_unit is None:
            return {'quote_id': quote.id, 'comparable': False, 'reason': err or 'conversion_unavailable'}
    landed = base_unit_price + extra_unit
    benchmark_price = float(getattr(benchmark, 'weighted_median_price', 0) or getattr(benchmark, 'median_price', 0) or 0)
    if benchmark_price <= 0:
        return {'quote_id': quote.id, 'comparable': False, 'reason': 'benchmark_unavailable', 'normalized_landed_unit_cost': round(landed, 6)}
    delta_pct = (landed - benchmark_price) / benchmark_price * 100
    return {'quote_id':quote.id,'supplier_name':quote.supplier_name,'comparable':True,'normalized_supplier_unit_price':round(base_unit_price,6),'normalized_extra_unit_cost':round(extra_unit,6),'normalized_landed_unit_cost':round(landed,6),'benchmark_unit_price':round(benchmark_price,6),'delta_pct':round(delta_pct,2),'market_room_per_unit':round(benchmark_price-landed,6),'market_room_pct':round((benchmark_price-landed)/benchmark_price*100,2),'band':'Below Benchmark' if delta_pct <= -10 else ('Above Benchmark' if delta_pct >= 10 else 'Near Benchmark'),'currency':target_currency,'unit':target_unit}
