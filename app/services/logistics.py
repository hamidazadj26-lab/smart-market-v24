from __future__ import annotations
from math import isfinite

VALID_MODES={'road','rail','sea','air','multimodal'}
VALID_INCOTERMS={'FOB','CFR','CIF','LANDED'}

def _n(v):
    v=float(v or 0)
    return v if isfinite(v) and v>=0 else 0.0

def calculate_logistics(*, fob_total, quantity, freight_total, insurance_percent=0, insurance_fixed=0, customs_total=0, destination_handling=0, other_cost=0):
    fob=_n(fob_total); q=_n(quantity); freight=_n(freight_total)
    insured_base=fob+freight
    insurance=insured_base*(_n(insurance_percent)/100.0)+_n(insurance_fixed)
    cfr=fob+freight
    cif=cfr+insurance
    landed=cif+_n(customs_total)+_n(destination_handling)+_n(other_cost)
    return {
        'fob_total':round(fob,6),'cfr_total':round(cfr,6),'cif_total':round(cif,6),'landed_total':round(landed,6),
        'freight_total':round(freight,6),'insurance_total':round(insurance,6),
        'customs_total':round(_n(customs_total),6),'destination_handling':round(_n(destination_handling),6),'other_cost':round(_n(other_cost),6),
        'fob_unit_price':round(fob/q,6) if q else 0,'cfr_unit_price':round(cfr/q,6) if q else 0,
        'cif_unit_price':round(cif/q,6) if q else 0,'landed_unit_price':round(landed/q,6) if q else 0,
        'insurance_base':round(insured_base,6),'quantity':q
    }

def scenario_summary(scenario, fob_total, quantity):
    return calculate_logistics(fob_total=fob_total, quantity=quantity, freight_total=scenario.freight_total,
        insurance_percent=scenario.insurance_percent, insurance_fixed=scenario.insurance_fixed,
        customs_total=scenario.customs_total, destination_handling=scenario.destination_handling,
        other_cost=scenario.other_cost)
