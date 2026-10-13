from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, HttpUrl

class SetupIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=200)
class LoginIn(SetupIn): pass
class AdminCreateIn(BaseModel):
    username:str=Field(min_length=3,max_length=80); password:str=Field(min_length=10,max_length=200); role:str=Field(default='Viewer',pattern=r'^(Super Admin|Admin|Sales|Procurement|Logistics|Analyst|Viewer)$')
class AdminRoleUpdateIn(BaseModel): role:str=Field(pattern=r'^(Super Admin|Admin|Sales|Procurement|Logistics|Analyst|Viewer)$')
class AdminStatusUpdateIn(BaseModel): is_active:bool

class ProductIn(BaseModel):
    name: str; category: str|None=None; sub_category: str|None=None; unit: str|None=None; aliases:list[str]=Field(default_factory=list); specifications:dict=Field(default_factory=dict)
class ManufacturerIn(BaseModel):
    name:str; company:str|None=None; product_id:int|None=None; country:str='Iran'; city:str|None=None; address:str|None=None; latitude:float|None=None; longitude:float|None=None; capacity_value:float|None=None; capacity_unit:str|None=None; phone:str|None=None; website:str|None=None; source_id:int|None=None; source_url:str|None=None; source_title:str|None=None; retrieved_at:datetime|None=None; verification_status:str='Unverified'; confidence:float=Field(default=0,ge=0,le=1)
class CustomerIn(BaseModel):
    name:str; country:str; city:str|None=None; address:str|None=None; latitude:float|None=None; longitude:float|None=None; activity_type:str|None=None; product_id:int|None=None; phone:str|None=None; website:str|None=None; source_id:int|None=None; source_url:str|None=None; source_title:str|None=None; retrieved_at:datetime|None=None; verification_status:str='Unverified'; confidence:float=Field(default=0,ge=0,le=1)

class SupplierIn(BaseModel):
    canonical_name: str = Field(min_length=2, max_length=250)
    country: str = Field(default='Iran', min_length=2, max_length=100)
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    verification_status: str = Field(default='Unverified', pattern='^(Unverified|Partially Verified|Verified|Rejected)$')
    confidence: float = Field(default=0, ge=0, le=1)
    trust_score: float = Field(default=0, ge=0, le=100)
    canonical_key: str | None = None

class BuyerIn(BaseModel):
    canonical_name: str = Field(min_length=2, max_length=250)
    country: str = Field(min_length=2, max_length=100)
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    verification_status: str = Field(default='Potential', pattern='^(Potential|Unverified|Partially Verified|Verified|Rejected)$')
    confidence: float = Field(default=0, ge=0, le=1)
    reliability_score: float = Field(default=0, ge=0, le=100)
    canonical_key: str | None = None

class CommercialFactIn(BaseModel):
    entity_type: str = Field(min_length=2, max_length=60)
    entity_id: int = Field(gt=0)
    fact_type: str = Field(min_length=2, max_length=100)
    value: dict = Field(default_factory=dict)
    source_signal_id: int | None = None
    evidence_id: int | None = None
    observed_at: datetime | None = None
    valid_until: datetime | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    status: str = Field(default='Unverified', pattern='^(Unverified|Partially Verified|Verified|Rejected)$')

class FXRateIn(BaseModel):
    base_currency: str = Field(min_length=3, max_length=10)
    quote_currency: str = Field(min_length=3, max_length=10)
    rate: float = Field(gt=0)
    source_id: int | None = None
    source_url: str | None = None
    observed_at: datetime | None = None
    expires_at: datetime | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    status: str = Field(default='Unverified', pattern='^(Unverified|Partially Verified|Verified|Rejected)$')

class AIInferenceIn(BaseModel):
    task_type: str = Field(min_length=2, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    model_version: str = Field(min_length=1, max_length=120)
    generated_at: datetime | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    evidence_ids: list[int] = Field(default_factory=list, max_length=500)
    input_hash: str | None = Field(default=None, min_length=64, max_length=64)
    output: dict = Field(default_factory=dict)

class DemandIn(BaseModel):
    product_id:int; raw_text:str|None=None; quantity:float|None=None; unit:str|None=None; country:str; city:str|None=None; latitude:float|None=None; longitude:float|None=None; urgency:str|None=None; source_id:int|None=None; source_url:str|None=None; published_at:datetime|None=None; verification_notes:str|None=None; confidence:float=Field(default=0,ge=0,le=1); verification_status:str='Unverified'
class SourceIn(BaseModel): source_type:str; name:str; base_url:str|None=None; allowed:bool=True; access_mode:str='manual'; capability:str='manual_entry'; configured:bool=False; authenticated:bool=False; availability_status:str='Unknown'; limitations:list[str]=Field(default_factory=list)
class SignalIn(BaseModel): source_id:int|None=None; raw_text:str; source_url:str|None=None; source_title:str|None=None; published_at:datetime|None=None; verification_status:str='Unverified'; confidence:float=Field(default=0,ge=0,le=1); normalized_payload:dict=Field(default_factory=dict)
class SearchIn(BaseModel): product:str; market:str|None=None; limit:int=Field(default=50,ge=1,le=200); external:bool=False
class RouteIn(BaseModel): origin:str; destination:str
class VerifyIn(BaseModel):
    status:str = Field(pattern='^(Unverified|Partially Verified|Verified|Rejected)$')
    evidence:dict = Field(default_factory=dict)
    reviewer:str|None=None
    notes:str|None=None
class VerificationOut(BaseModel):
    entity_type:str; entity_id:int; status:str; evidence:dict; reviewer:str|None=None


class DiscoveryRunIn(BaseModel):
    product: str | None = None
    signal_ids: list[int] = Field(default_factory=list)
    texts: list[str] = Field(default_factory=list)
    market: str | None = None

class DiscoveryPlaceIn(BaseModel):
    signal_id: int
    place: dict

class ExternalDiscoveryIn(BaseModel):
    product: str
    market: str | None = None
    max_results: int = Field(default=20, ge=1, le=50)
    sources: list[str] = Field(default_factory=lambda: ['web', 'places'], max_length=20)
    query_terms: list[str] = Field(default_factory=list, max_length=20)
    domains: list[str] = Field(default_factory=list, max_length=20)

class SignalIngestItem(BaseModel):
    source_id: int | None = None
    raw_text: str
    source_url: str | None = None
    source_title: str | None = None
    published_at: datetime | None = None
    external_key: str | None = None

class CandidateReviewIn(BaseModel):
    status: str = Field(pattern='^(Review|Accepted|Rejected)$')

class EvidenceIn(BaseModel):
    entity_type: str
    entity_id: int
    source_signal_id: int | None = None
    evidence_type: str = Field(min_length=2, max_length=80)
    weight: float = Field(default=0.5, ge=0, le=1)
    excerpt: str | None = None
    source_url: str | None = None
    details: dict = Field(default_factory=dict)

class CandidateMergeIn(BaseModel):
    duplicate_ids: list[int] = Field(default_factory=list, max_length=50)

class OpportunityActionIn(BaseModel):
    action_type: str = Field(pattern='^(call|whatsapp|email|rfq|follow_up|meeting|note|other)$')
    status: str = Field(default='Planned', pattern='^(Planned|In Progress|Completed|Cancelled)$')
    subject: str | None = None
    notes: str | None = None
    channel: str | None = None
    due_at: datetime | None = None
    result: str | None = None

class RFQGenerateIn(BaseModel):
    channel: str = Field(default='whatsapp', pattern='^(whatsapp|email|rfq)$')
    language: str = Field(default='en', pattern='^(en|fa|ps)$')
    tone: str = Field(default='professional', pattern='^(professional|concise)$')

class RFQUpdateIn(BaseModel):
    status: str = Field(default='Draft', pattern='^(Draft|Approved|Sent|Responded|Closed|Cancelled)$')
    response_due_at: datetime | None = None

class CommunicationIn(BaseModel):
    channel: str = Field(pattern='^(whatsapp|email|phone|telegram|other)$')
    direction: str = Field(default='outbound', pattern='^(outbound|inbound)$')
    status: str = Field(default='Draft', pattern='^(Draft|Sent|Received|Failed)$')
    recipient: str | None = None
    subject: str | None = None
    message: str = Field(min_length=1, max_length=20000)
    response_summary: str | None = None
    sent_at: datetime | None = None

class SupplierQuoteIn(BaseModel):
    manufacturer_id:int|None=None
    supplier_name:str
    currency:str='USD'
    unit_price:float=Field(gt=0)
    quantity:float=Field(gt=0)
    unit:str='kg'
    incoterm:str='EXW'
    freight_cost:float=Field(default=0,ge=0)
    other_cost:float=Field(default=0,ge=0)
    lead_time_days:int|None=Field(default=None,ge=0)
    validity_days:int|None=Field(default=None,ge=0)
    notes:str|None=None
    source_url:str|None=None
    status:str='Unverified'

class CommercialOfferIn(BaseModel):
    supplier_quote_id:int|None=None
    fx_rate_id:int|None=None
    currency:str='USD'
    exchange_rate:float=Field(default=1,gt=0, description='Legacy response field; server derives FX from FXRate.')
    quantity:float=Field(gt=0)
    unit:str='kg'
    supplier_unit_price:float=Field(default=0,ge=0)
    packaging_cost:float=Field(default=0,ge=0)
    inland_cost:float=Field(default=0,ge=0)
    export_cost:float=Field(default=0,ge=0)
    freight_cost:float=Field(default=0,ge=0)
    insurance_cost:float=Field(default=0,ge=0)
    customs_cost:float=Field(default=0,ge=0)
    other_cost:float=Field(default=0,ge=0)
    commission_percent:float=Field(default=0,ge=0,le=100)
    commission_fixed:float=Field(default=0,ge=0)
    target_margin_percent:float=Field(default=10,ge=0,le=100)
    status:str='Draft'
    notes:str|None=None
    assumptions:dict=Field(default_factory=dict)
    logistics_scenario_id:int|None=None
    incoterm:str=Field(default='CIF',pattern='^(FOB|CFR|CIF|LANDED)$')

class CommercialOfferUpdateIn(CommercialOfferIn):
    pass

class LogisticsScenarioIn(BaseModel):
    name:str=Field(min_length=2,max_length=200)
    origin:str=Field(min_length=2,max_length=250)
    destination:str=Field(min_length=2,max_length=250)
    transport_mode:str=Field(default='road',pattern='^(road|rail|sea|air|multimodal)$')
    border_or_port:str|None=None
    distance_km:float|None=Field(default=None,ge=0)
    transit_days:float|None=Field(default=None,ge=0)
    freight_total:float=Field(default=0,ge=0)
    currency:str='USD'
    insurance_percent:float=Field(default=0,ge=0,le=100)
    insurance_fixed:float=Field(default=0,ge=0)
    customs_total:float=Field(default=0,ge=0)
    destination_handling:float=Field(default=0,ge=0)
    other_cost:float=Field(default=0,ge=0)
    capacity_value:float|None=Field(default=None,ge=0)
    capacity_unit:str|None=None
    source_url:str|None=None
    source_title:str|None=None
    verification_status:str='Unverified'
    assumptions:dict=Field(default_factory=dict)

class LogisticsCalculateIn(BaseModel):
    fob_total:float=Field(ge=0)
    quantity:float=Field(gt=0)
    freight_total:float=Field(default=0,ge=0)
    insurance_percent:float=Field(default=0,ge=0,le=100)
    insurance_fixed:float=Field(default=0,ge=0)
    customs_total:float=Field(default=0,ge=0)
    destination_handling:float=Field(default=0,ge=0)
    other_cost:float=Field(default=0,ge=0)

class CommercialComparisonIn(BaseModel):
    quantity:float|None=Field(default=None,gt=0)
    base_currency:str='USD'
    fx_rates:dict[str,float]=Field(default_factory=dict)

class CommercialComparisonSelectIn(BaseModel):
    quote_id:int
    scenario_id:int
    quantity:float=Field(gt=0)
    unit:str='kg'
    target_margin_percent:float=Field(default=10,ge=0,lt=100)
    currency:str='USD'
    exchange_rate:float=Field(default=1,gt=0)
    status:str='Draft'
    notes:str|None=None

class TransactionCreateIn(BaseModel):
    commercial_offer_id:int|None=None
    quantity:float|None=Field(default=None,gt=0)
    unit:str|None=None
    agreed_unit_price:float|None=Field(default=None,gt=0)
    agreed_total:float|None=Field(default=None,gt=0)
    currency:str|None=None
    incoterm:str|None=None
    notes:str|None=None

class TransactionTransitionIn(BaseModel):
    status:str=Field(pattern='^(Draft|Confirmed|Payment Pending|Paid|Preparing|Shipped|In Transit|Delivered|Completed|Cancelled|Disputed)$')
    notes:str|None=None
    payload:dict=Field(default_factory=dict)

class TransactionOutcomeIn(BaseModel):
    actual_quantity:float|None=Field(default=None,gt=0)
    actual_unit_price:float|None=Field(default=None,gt=0)
    actual_total:float|None=Field(default=None,gt=0)
    actual_freight:float|None=Field(default=None,ge=0)
    actual_delivery_days:float|None=Field(default=None,ge=0)
    outcome:dict=Field(default_factory=dict)
    notes:str|None=None

class MarketPriceObservationIn(BaseModel):
    product_id:int
    market:str
    country:str|None=None
    city:str|None=None
    grade:str|None=None
    specification:dict={}
    price:float=Field(gt=0)
    currency:str='USD'
    unit:str='kg'
    incoterm:str|None=None
    quantity:float|None=Field(default=None,gt=0)
    source_id:int|None=None
    source_url:str|None=None
    source_title:str|None=None
    observed_at:datetime|None=None
    verification_status:str=Field(default='Unverified',pattern='^(Unverified|Partially Verified|Verified|Rejected)$')
    confidence:float=Field(default=0.0,ge=0,le=1)
    notes:str|None=None

class MarketBenchmarkIn(BaseModel):
    product_id:int
    market:str
    country:str|None=None
    grade:str|None=None
    unit:str='kg'
    incoterm:str|None=None
    target_currency:str='USD'
    fx_rates:dict[str,float]=Field(default_factory=dict)
    unit_factors:dict[str,float]={}
    min_effective:int=Field(default=3,ge=1,le=100)

class MarketBenchmarkCompareIn(BaseModel):
    price:float=Field(gt=0)
    currency:str='USD'
    unit:str='kg'
    fx_rates:dict[str,float]=Field(default_factory=dict)
    unit_factors:dict[str,float]={}

class OpportunityPriceIntelligenceIn(BaseModel):
    benchmark_id:int|None=None
    target_currency:str='USD'
    target_unit:str='kg'
    fx_rates:dict[str,float]=Field(default_factory=dict)
    unit_factors:dict[str,float]={}

class DealDecisionEngineIn(BaseModel):
    quote_id:int|None=None
    benchmark_id:int|None=None
    target_currency:str='USD'
    target_unit:str='kg'
    fx_rates:dict[str,float]=Field(default_factory=dict)
    unit_factors:dict[str,float]={}
    target_margin_percent:float=Field(default=10,ge=0,lt=100)
    minimum_margin_percent:float=Field(default=0,ge=0,lt=100)
    selling_commission_percent:float=Field(default=0,ge=0,lt=100)
    selling_commission_fixed_per_unit:float=Field(default=0,ge=0)
    quantity:float=Field(default=1,gt=0)

class NegotiationIntelligenceIn(BaseModel):
    quote_id:int|None=None
    benchmark_id:int|None=None
    target_currency:str='USD'
    target_unit:str='kg'
    fx_rates:dict[str,float]=Field(default_factory=dict)
    unit_factors:dict[str,float]={}
    target_margin_percent:float=Field(default=10,ge=0,lt=100)
    minimum_margin_percent:float=Field(default=0,ge=0,lt=100)
    selling_commission_percent:float=Field(default=0,ge=0,lt=100)
    selling_commission_fixed_per_unit:float=Field(default=0,ge=0)
    opening_buffer_percent:float=Field(default=5,ge=0,lt=100)
    concession_steps:list[float]=Field(default_factory=list)
    quantity:float=Field(default=1,gt=0)

class OpportunityWorkspaceCommandIn(BaseModel):
    command: str = Field(pattern='^(action|supplier_quote|logistics_scenario|communication)$')
    action: OpportunityActionIn | None = None
    supplier_quote: SupplierQuoteIn | None = None
    logistics_scenario: LogisticsScenarioIn | None = None
    communication: CommunicationIn | None = None


class OpportunityStageTransitionIn(BaseModel):
    stage: str = Field(pattern='^(Discovered|Verified|Qualified|RFQ Sent|Supplier Quoted|Logistics Priced|Commercial Offer|Negotiation|Won|Lost)$')
    reason: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    owner_id: int | None = None
    next_action: str | None = Field(default=None, max_length=2000)

class OpportunityStageConfigOut(BaseModel):
    stage: str
    order: int
    terminal: bool
    required_evidence: list[str]


class DataQualityGateIn(BaseModel):
    acknowledge_warnings: bool = False


class MarketProfileIn(BaseModel):
    name:str=Field(min_length=3,max_length=200)
    source_country:str=Field(min_length=2,max_length=100)
    target_country:str=Field(min_length=2,max_length=100)
    active:bool=True
    default_currency:str='USD'
    languages:list[str]=[]
    incoterms:list[str]=[]
    transport_modes:list[str]=[]
    scoring_weights:dict[str,float]={}
    commercial_rules:dict={}


class CountryProfileIn(BaseModel):
    country_code:str=Field(min_length=2,max_length=10)
    country_name:str=Field(min_length=2,max_length=120)
    currencies:list[str]=[]
    languages:list[str]=[]
    payment_methods:list[str]=[]
    customs_notes:dict={}
    logistics_nodes:list[dict]=[]
    source_url:str|None=None
    source_title:str|None=None
    retrieved_at:datetime|None=None
    verification_status:str='Unverified'

class TradeRuleIn(BaseModel):
    market_id:int
    country_profile_id:int|None=None
    rule_type:str=Field(min_length=2,max_length=50)
    title:str=Field(min_length=2,max_length=300)
    hs_code:str|None=None
    product_scope:str|None=None
    mandatory:bool=True
    status:str='Unverified'
    requirement:str=Field(min_length=2)
    documents:list[str]=[]
    authority:str|None=None
    source_url:str|None=None
    source_title:str|None=None
    published_at:datetime|None=None
    effective_from:datetime|None=None
    effective_to:datetime|None=None
    notes:str|None=None


class ProductComplianceIn(BaseModel):
    product_id:int
    market_id:int
    hs_code:str=Field(min_length=2,max_length=30)
    hs_description:str|None=None
    classification_basis:str|None=None
    status:str='Unverified'
    confidence:float=Field(default=0,ge=0,le=1)
    source_url:str|None=None
    source_title:str|None=None
    notes:str|None=None

class ImportCostRuleIn(BaseModel):
    market_id:int
    hs_code:str=Field(min_length=2,max_length=30)
    product_scope:str|None=None
    duty_percent:float=Field(default=0,ge=0,le=100)
    excise_percent:float=Field(default=0,ge=0,le=100)
    vat_percent:float=Field(default=0,ge=0,le=100)
    other_percent:float=Field(default=0,ge=0,le=100)
    fixed_fee:float=Field(default=0,ge=0)
    currency:str='USD'
    vat_base:str=Field(default='customs_plus_duty',pattern='^(customs_value|customs_plus_duty|customs_plus_duty_excise)$')
    other_base:str=Field(default='customs_value',pattern='^(customs_value|customs_plus_duty|customs_plus_duty_excise|taxable_total)$')
    status:str='Unverified'
    authority:str|None=None
    source_url:str|None=None
    source_title:str|None=None
    published_at:datetime|None=None
    effective_from:datetime|None=None
    effective_to:datetime|None=None
    notes:str|None=None

class ImportCostCalculateIn(BaseModel):
    customs_value:float=Field(gt=0)
    currency:str='USD'
    quantity:float=Field(default=1,gt=0)
    include_fixed_fee:bool=True

class ComplianceRequirementIn(BaseModel):
    product_compliance_id:int
    trade_rule_id:int|None=None
    requirement_type:str=Field(min_length=2,max_length=50)
    title:str=Field(min_length=2,max_length=300)
    mandatory:bool=True
    status:str='Unverified'
    documents:list[str]=[]
    evidence:dict={}
    source_url:str|None=None
    source_title:str|None=None
    notes:str|None=None

class LandedCostIn(BaseModel):
    quantity:float=Field(gt=0)
    unit:str='kg'
    currency:str='USD'
    supplier_cost:float=Field(ge=0)
    packaging_cost:float=Field(default=0,ge=0)
    inland_cost:float=Field(default=0,ge=0)
    export_cost:float=Field(default=0,ge=0)
    freight_cost:float=Field(default=0,ge=0)
    insurance_cost:float=Field(default=0,ge=0)
    customs_value:float|None=Field(default=None,ge=0)
    destination_handling:float=Field(default=0,ge=0)
    other_cost:float=Field(default=0,ge=0)
    fx_rate:float|None=Field(default=None,gt=0)
    target_currency:str|None=None
    hs_code:str|None=None
    import_cost_rule_id:int|None=None
    logistics_scenario_id:int|None=None
    persist:bool=False

class TradeRouteProfileIn(BaseModel):
    name:str=Field(min_length=2,max_length=200)
    origin:str=Field(min_length=2,max_length=250)
    destination:str=Field(min_length=2,max_length=250)
    market_id:int|None=None
    currency:str='USD'
    verification_status:str=Field(default='Unverified',pattern='^(Unverified|Partially Verified|Verified|Rejected)$')
    source_url:str|None=None
    source_title:str|None=None
    assumptions:dict=Field(default_factory=dict)

class TradeRouteSegmentIn(BaseModel):
    sequence:int=Field(default=1,ge=1)
    segment_type:str=Field(default='transport',pattern='^(transport|border|port|handling|transit)$')
    from_location:str=Field(min_length=2,max_length=250)
    to_location:str=Field(min_length=2,max_length=250)
    transport_mode:str=Field(default='road',pattern='^(road|rail|sea|air|multimodal|none)$')
    border_or_port:str|None=None
    distance_km:float|None=Field(default=None,ge=0)
    transit_days:float|None=Field(default=None,ge=0)
    freight_cost:float=Field(default=0,ge=0)
    border_cost:float=Field(default=0,ge=0)
    transit_cost:float=Field(default=0,ge=0)
    destination_handling:float=Field(default=0,ge=0)
    other_cost:float=Field(default=0,ge=0)
    currency:str='USD'
    verification_status:str=Field(default='Unverified',pattern='^(Unverified|Partially Verified|Verified|Rejected)$')
    source_url:str|None=None
    assumptions:dict=Field(default_factory=dict)

class TradeRouteCalculateIn(BaseModel):
    quantity:float=Field(gt=0)
    currency:str='USD'
    fx_rates:dict[str,float]=Field(default_factory=dict)

class TradeOptimizationIn(BaseModel):
    quote_ids:list[int]=Field(min_length=1, max_length=50)
    route_ids:list[int]=Field(min_length=1, max_length=50)
    quantity:float=Field(gt=0)
    target_currency:str='USD'
    fx_rates:dict[str,float]=Field(default_factory=dict)
    customs_values:dict[str,float]={}
    limit:int=Field(default=100,ge=1,le=500)

class TradeOptimizationApplyIn(BaseModel):
    result_id:int
    target_margin_percent:float=Field(default=10,ge=0,lt=100)
    commission_percent:float=Field(default=0,ge=0,le=100)
    commission_fixed:float=Field(default=0,ge=0)
    status:str='Draft'
    notes:str|None=None
