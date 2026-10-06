from __future__ import annotations
from math import isfinite


def _n(v, default=0.0):
    try: v=float(v if v is not None else default)
    except (TypeError, ValueError): return default
    return v if isfinite(v) else default


def compare_supplier_routes(quotes, scenarios, *, quantity=None, base_currency='USD', fx_rates=None):
    """Build a transparent supplier x route comparison matrix.

    fx_rates maps source currency -> base_currency (e.g. {'IRR': 0.000005}).
    A missing FX rate does not guess; that combination is marked non-comparable.
    """
    fx_rates = fx_rates or {base_currency: 1.0}
    rows=[]
    for q in quotes:
        qqty=_n(quantity if quantity is not None else q.quantity)
        if qqty <= 0: continue
        qfx=fx_rates.get(q.currency)
        for s in scenarios:
            if not s.is_active: continue
            sfx=fx_rates.get(s.currency)
            if qfx is None or sfx is None or q.currency not in fx_rates or s.currency not in fx_rates:
                rows.append({'quote_id':q.id,'scenario_id':s.id,'comparable':False,'reason':'نرخ تبدیل ارز برای یکی از ارزها ثبت نشده است.','currency':base_currency})
                continue
            supplier_unit_base=_n(q.unit_price)*qfx
            quote_additional=(_n(q.freight_cost)+_n(q.other_cost))/qqty*qfx
            supplier_unit=supplier_unit_base+quote_additional
            # Do not double-count freight already covered by a delivered Incoterm.
            inc=(q.incoterm or 'EXW').upper()
            route_applies=inc not in {'CIF','CIP','DAP','DDP','LANDED'}
            scenario_freight=_n(s.freight_total)/qqty*sfx if route_applies else 0.0
            scenario_insurance_base=(supplier_unit*qqty/sfx + _n(s.freight_total)) if route_applies else 0.0
            insurance=(scenario_insurance_base*(_n(s.insurance_percent)/100)+_n(s.insurance_fixed))*sfx/qqty if route_applies else 0.0
            customs=(_n(s.customs_total)+_n(s.destination_handling)+_n(s.other_cost))*sfx/qqty if route_applies else 0.0
            landed_unit=supplier_unit+scenario_freight+insurance+customs
            lead=q.lead_time_days if q.lead_time_days is not None else 9999
            transit=(s.transit_days if s.transit_days is not None else 9999)
            total_days=lead+transit
            verification_bonus=15 if q.status=='Verified' else 8 if q.status=='Partially Verified' else 0
            route_bonus=10 if s.verification_status=='Verified' else 5 if s.verification_status=='Partially Verified' else 0
            cost_score=max(0.0,100.0-min(100.0,landed_unit/(max(supplier_unit,0.000001)*2)*100))
            speed_score=max(0.0,100.0-min(100.0,total_days/60*100))
            score=cost_score*0.55+speed_score*0.20+verification_bonus+route_bonus
            reasons=[f'هزینه واحد برآوردی {landed_unit:.4f} {base_currency}']
            if route_applies: reasons.append('هزینه حمل سناریو به‌صورت جداگانه اعمال شد')
            else: reasons.append(f'Incoterm {inc} پوشش حمل/تحویل را در قیمت تأمین‌کننده لحاظ می‌کند؛ از دوباره‌شماری جلوگیری شد')
            rows.append({'quote_id':q.id,'scenario_id':s.id,'comparable':True,'supplier_name':q.supplier_name,'scenario_name':s.name,'supplier_currency':q.currency,'route_currency':s.currency,'currency':base_currency,'incoterm':inc,'supplier_unit_base':round(supplier_unit,6),'route_cost_unit':round(scenario_freight+insurance+customs,6),'landed_unit_estimate':round(landed_unit,6),'lead_time_days':q.lead_time_days,'transit_days':s.transit_days,'total_days':None if total_days>=9999 else round(total_days,2),'score':round(score,4),'reasons':reasons})
    comparable=[r for r in rows if r.get('comparable')]
    comparable.sort(key=lambda r:(-r['score'],r['landed_unit_estimate'],r['total_days'] if r['total_days'] is not None else 9999))
    for i,r in enumerate(comparable,1): r['rank']=i
    return rows
