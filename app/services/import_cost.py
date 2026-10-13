from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models import ImportCostRule, Market

STATUSES={'Verified','Partially Verified','Unverified','Expired','Rejected'}
VAT_BASES={'customs_value','customs_plus_duty','customs_plus_duty_excise'}
OTHER_BASES={'customs_value','customs_plus_duty','customs_plus_duty_excise','taxable_total'}

def now(): return datetime.now(timezone.utc)

def is_current(rule, at=None):
    at=at or now()
    if rule.status!='Verified': return False
    if rule.effective_from and rule.effective_from>at: return False
    if rule.effective_to and rule.effective_to<at: return False
    return True

def serialize_rule(r):
    return {c.name:getattr(r,c.name) for c in r.__table__.columns}

def find_verified_rule(db:Session, market_id:int, hs_code:str, product_scope=None):
    q=db.query(ImportCostRule).filter(ImportCostRule.market_id==market_id,ImportCostRule.hs_code==hs_code)
    rows=[r for r in q.order_by(ImportCostRule.updated_at.desc()).all() if is_current(r)]
    if product_scope:
        exact=[r for r in rows if r.product_scope and (r.product_scope.lower() in product_scope.lower() or product_scope.lower() in r.product_scope.lower())]
        if exact: rows=exact
    return rows[0] if rows else None

def calculate_import_cost(rule, customs_value, quantity=1, include_fixed_fee=True):
    cv=float(customs_value)
    if cv<=0: raise ValueError('customs_value must be > 0')
    duty=cv*float(rule.duty_percent)/100
    excise_base=cv+duty
    excise=excise_base*float(rule.excise_percent)/100
    bases={'customs_value':cv,'customs_plus_duty':cv+duty,'customs_plus_duty_excise':cv+duty+excise}
    vat_base=bases[rule.vat_base]
    vat=vat_base*float(rule.vat_percent)/100
    other_base={'customs_value':cv,'customs_plus_duty':cv+duty,'customs_plus_duty_excise':cv+duty+excise,'taxable_total':cv+duty+excise+vat}[rule.other_base]
    other=other_base*float(rule.other_percent)/100
    fixed=float(rule.fixed_fee) if include_fixed_fee else 0.0
    total=duty+excise+vat+other+fixed
    return {'customs_value':round(cv,6),'duty':round(duty,6),'excise':round(excise,6),'vat':round(vat,6),'other_tax_or_fee':round(other,6),'fixed_fee':round(fixed,6),'total_import_taxes_and_fees':round(total,6),'landed_before_other_logistics':round(cv+total,6),'taxes_and_fees_per_unit':round(total/float(quantity),6),'landed_before_other_logistics_per_unit':round((cv+total)/float(quantity),6),'quantity':float(quantity),'currency':rule.currency,'rule_id':rule.id,'basis':{'vat_base':rule.vat_base,'other_base':rule.other_base},'assumptions':{'customs_value_is_already_normalized':True,'no_fx_conversion_performed':True,'no_freight_or_insurance_added_by_engine':True}}
