from __future__ import annotations
from datetime import datetime, timezone, timedelta
from statistics import median
from sqlalchemy.orm import Session

from ..models import Opportunity, Market, MarketPriceObservation, MarketPriceBenchmark, Verification, VerificationEvidence, Customer, Manufacturer, Demand


def _utc(v):
    if not v: return None
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v


def _age_days(v, now=None):
    if not v: return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - _utc(v)).total_seconds() / 86400)


def freshness(v, half_life_days=30, now=None):
    age = _age_days(v, now)
    if age is None: return 0.0
    return round(0.5 ** (age / max(1, half_life_days)), 4)


def trend(values):
    if len(values) < 2:
        return {'direction':'Insufficient Data','change_pct':None,'slope':None}
    values = [float(x) for x in values]
    n=len(values); xs=list(range(n)); mx=(n-1)/2
    my=sum(values)/n
    denom=sum((x-mx)**2 for x in xs)
    slope=sum((x-mx)*(y-my) for x,y in zip(xs,values))/denom if denom else 0.0
    base=values[0]
    change=((values[-1]-base)/base*100) if base else None
    if slope > 0.0001: direction='Rising'
    elif slope < -0.0001: direction='Falling'
    else: direction='Stable'
    return {'direction':direction,'change_pct':round(change,2) if change is not None else None,'slope':round(slope,6)}


def market_price_trend(db: Session, product_id:int, market:str, days:int=90, currency:str|None=None, unit:str|None=None, now=None):
    now=now or datetime.now(timezone.utc); start=now-timedelta(days=max(1,min(days,3650)))
    q=db.query(MarketPriceObservation).filter(MarketPriceObservation.product_id==product_id, MarketPriceObservation.market==market, MarketPriceObservation.observed_at>=start)
    if currency: q=q.filter(MarketPriceObservation.currency==currency)
    if unit: q=q.filter(MarketPriceObservation.unit==unit)
    rows=q.order_by(MarketPriceObservation.observed_at.asc()).all()
    points=[{'observed_at':_utc(x.observed_at).isoformat() if x.observed_at else None,'price':x.price,'currency':x.currency,'unit':x.unit,'grade':x.grade,'incoterm':x.incoterm,'verification_status':x.verification_status,'confidence':x.confidence} for x in rows]
    t=trend([x['price'] for x in points])
    return {'product_id':product_id,'market':market,'days':days,'count':len(points),'trend':t,'points':points}


def _entity_freshness(db, entity_type, entity_id, now):
    entity={'customer':Customer,'manufacturer':Manufacturer,'demand':Demand}.get(entity_type)
    obj=db.get(entity,entity_id) if entity else None
    if not obj: return 0.0, None
    stamp=getattr(obj,'retrieved_at',None) or getattr(obj,'published_at',None) or getattr(obj,'updated_at',None) or getattr(obj,'created_at',None)
    return freshness(stamp,30,now), stamp


def opportunity_temporal_intelligence(db: Session, op: Opportunity, days:int=90, now=None):
    now=now or datetime.now(timezone.utc)
    market_obj=db.get(Market, op.market_id) if op.market_id else None
    market_name=market_obj.name if market_obj else None
    price_trend=market_price_trend(db,op.product_id,market_name,days=days,now=now) if market_name else {'product_id':op.product_id,'market':None,'days':days,'count':0,'trend':trend([]),'points':[]}
    # If no exact market observation exists, use any market for the product as a transparent fallback.
    if not price_trend['count']:
        q=db.query(MarketPriceObservation).filter(MarketPriceObservation.product_id==op.product_id,MarketPriceObservation.observed_at>=now-timedelta(days=days)).order_by(MarketPriceObservation.observed_at.asc()).all()
        vals=[x.price for x in q]
        price_trend={'product_id':op.product_id,'market':'all available markets','days':days,'count':len(vals),'trend':trend(vals),'points':[{'observed_at':_utc(x.observed_at).isoformat() if x.observed_at else None,'price':x.price,'currency':x.currency,'unit':x.unit,'confidence':x.confidence} for x in q]}
    entities={}
    for et,eid in [('customer',op.customer_id),('manufacturer',op.manufacturer_id)]+([('demand',op.demand_id)] if op.demand_id else []):
        f,stamp=_entity_freshness(db,et,eid,now); entities[et]={'freshness_score':round(f*100,2),'last_observed_at':_utc(stamp).isoformat() if stamp else None,'age_days':round(_age_days(stamp,now),2) if stamp else None}
    stage_age=_age_days(op.stage_updated_at,now) or 0
    health_direction='Improving' if stage_age <= 3 and op.opportunity_stage not in ('Won','Lost') else ('Stagnating' if stage_age <= 14 else 'Stale')
    benchmark=db.query(MarketPriceBenchmark).filter(MarketPriceBenchmark.product_id==op.product_id).order_by(MarketPriceBenchmark.as_of.desc()).first()
    benchmark_age=_age_days(benchmark.as_of,now) if benchmark else None
    benchmark_fresh=freshness(benchmark.as_of,30,now) if benchmark else 0.0
    verification_rows=[]
    for et,eid in [('customer',op.customer_id),('manufacturer',op.manufacturer_id)]+([('demand',op.demand_id)] if op.demand_id else []):
        verification_rows += db.query(Verification).filter(Verification.entity_type==et,Verification.entity_id==eid).order_by(Verification.created_at.desc()).limit(10).all()
    verification_age=_age_days(verification_rows[0].created_at,now) if verification_rows else None
    verification_fresh=freshness(verification_rows[0].created_at,45,now) if verification_rows else 0.0
    source_age=min((x['age_days'] for x in entities.values() if x['age_days'] is not None),default=None)
    signals=[]
    if price_trend['trend']['direction']=='Rising': signals.append({'type':'market_price','direction':'Rising','message':'قیمت‌های مشاهده‌شده بازار در بازه انتخابی روند افزایشی دارند.'})
    elif price_trend['trend']['direction']=='Falling': signals.append({'type':'market_price','direction':'Falling','message':'قیمت‌های مشاهده‌شده بازار در بازه انتخابی روند کاهشی دارند.'})
    if benchmark and benchmark_age is not None and benchmark_age>45: signals.append({'type':'benchmark_stale','direction':'Stale','message':'Benchmark بازار قدیمی است و بهتر است بازبینی شود.'})
    for et,v in entities.items():
        if v['age_days'] is not None and v['age_days']>45: signals.append({'type':f'{et}_stale','direction':'Stale','message':f'اطلاعات {et} بیش از ۴۵ روز به‌روزرسانی نشده است.'})
    if stage_age>14 and op.opportunity_stage not in ('Won','Lost'): signals.append({'type':'opportunity_stale','direction':'Stale','message':'فرصت بیش از ۱۴ روز در مرحله فعلی مانده است.'})
    data_points=[]
    for v in entities.values(): data_points.append(v['freshness_score'])
    data_points += [benchmark_fresh*100, verification_fresh*100, 100 if stage_age<=3 else max(0,100-stage_age*4)]
    temporal_score=round(sum(data_points)/len(data_points),2) if data_points else 0.0
    direction='Improving' if temporal_score>=75 and not any(s['direction']=='Stale' for s in signals) else ('Deteriorating' if temporal_score<45 or len(signals)>=3 else 'Watch')
    return {'opportunity_id':op.id,'as_of':now.isoformat(),'temporal_score':temporal_score,'direction':direction,'stage_age_days':round(stage_age,2),'stage_health':health_direction,'price_trend':price_trend['trend'],'price_observation_count':price_trend['count'],'benchmark':{'id':benchmark.id if benchmark else None,'age_days':round(benchmark_age,2) if benchmark_age is not None else None,'freshness_score':round(benchmark_fresh*100,2),'as_of':_utc(benchmark.as_of).isoformat() if benchmark and benchmark.as_of else None},'entities':entities,'verification_freshness_score':round(verification_fresh*100,2),'signals':signals,'recommendations':[{'priority':'high','action':'Refresh stale evidence','reason':'اطلاعات کلیدی قدیمی شده است.'} for _ in [1] if any(s['direction']=='Stale' for s in signals)] + ([{'priority':'medium','action':'Review market benchmark','reason':'روند قیمت یا Benchmark نیازمند بازبینی است.'}] if price_trend['count']>=2 and price_trend['trend']['direction']!='Stable' else [])}
