
## V21.0 Commercial Intelligence

### Production runtime contract (V24.17 Phase 1)
- API service: Dockerfile + `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Worker service: `Dockerfile.worker` + `python -m app.discovery.worker`
- Required production dependencies: PostgreSQL and Redis. SQLite is development/test only.
- `/api/health` returns HTTP 503 when any critical production dependency (DB, Redis, migrations, worker heartbeat) is unhealthy.
- Worker liveness is shared through Redis key `WORKER_HEARTBEAT_KEY`; no process-local health state is trusted.

- Supplier quotes per opportunity with supplier comparison and landed-unit estimate.
- Commercial offer calculator for FOB/CIF, freight, insurance, customs, commission and target margin.
- Commercial offer persistence with audit trail.
- Currency/exchange-rate field is explicit; no live FX rate is fabricated.
- API: `/api/opportunities/{id}/supplier-quotes`, `/api/opportunities/{id}/commercial-offers`, `/api/opportunities/{id}/commercial-offers/calculate`, `/api/commercial-intelligence`.

## V21.1 Logistics Intelligence
- Persisted logistics scenarios per opportunity: road/rail/sea/air/multimodal, origin/destination, border/port, distance, transit time, freight, insurance, customs and handling.
- Correct Incoterm-style calculation layers: FOB → CFR → CIF → estimated landed cost. Customs and destination handling are kept outside CIF.
- Google Routes can seed a road logistics scenario when a configured API key is available.
- Multiple scenarios can be compared externally through the scenario API; no freight rate is fabricated.
- Commercial offers can reference a logistics scenario so freight/insurance/customs are applied once.
- Migration: 0009_logistics_intelligence.

## V21.2 Supplier & Route Comparison
V21.2 adds a transparent supplier × logistics scenario comparison engine. It compares supplier quotes and active logistics scenarios, supports explicit FX rates, prevents currency guessing, exposes landed-unit estimates, lead-time components, score reasons, and allows an operator to select a quote+route pair to create a Commercial Offer.

## V21.3 Market Price Intelligence
V21.3 adds market price observations and transparent price benchmarks. Observations are scoped by product, market, country, grade, unit and Incoterm. Benchmarks expose low/P25/median/P75/high, a recency- and verification-weighted median, dispersion and confidence. Currency conversion and unit conversion require explicit rates/factors; the system never invents an FX rate or unit conversion. Supplier prices can be compared to a benchmark as Below/Near/Above Benchmark.

### New endpoints
- `GET /api/market-prices/observations`
- `POST /api/market-prices/observations`
- `POST /api/market-prices/benchmark`
- `GET /api/market-prices/benchmarks`
- `POST /api/market-prices/benchmarks/{benchmark_id}/compare`

Migration: `0010_market_price_intelligence`.

## V21.4 Market Intelligence Dashboard
V21.4 extends V21.3 from benchmark calculation into an operator-facing market intelligence layer:
- Dashboard endpoint for benchmark, confidence, market range, source diversity and price alerts.
- Time-bucketed price trend endpoint for recent observations.
- Source diversity can incorporate persisted `SourceTrust` scores when available.
- Benchmark observation queries no longer require an exact source unit; explicit unit factors can normalize cross-unit observations.
- Mobile-first UI adds a Market Intelligence action beside Price Benchmark.

### New endpoints
- `GET /api/market-prices/dashboard`
- `GET /api/market-prices/trend`

V21.4 remains evidence-first: no missing FX or unit conversion is guessed, and alerts are descriptive deviations from the stored benchmark rather than deal recommendations.

## V22.6 — Supplier Price vs Market Benchmark Intelligence
- Compares supplier quotes attached to an opportunity against the latest compatible market benchmark.
- Calculates normalized supplier unit price, landed unit cost, market room per unit and percentage deviation.
- Requires explicit FX rates and explicit unit-conversion factors; the system never guesses a currency or unit conversion.
- Endpoint: `POST /api/opportunities/{opportunity_id}/price-intelligence`.

## V21.6 — Profit & Deal Decision Engine
- Transparent deal economics for each Opportunity and Supplier Quote.
- Calculates landed unit cost, minimum-margin price, target-margin price, market ceiling, market room, total values and profit per unit.
- Supports selling commission as a percentage and fixed per-unit amount.
- Requires explicit FX and unit conversions; no currency/unit guessing.
- Endpoint: `POST /api/opportunities/{opportunity_id}/deal-decision`.
- The engine reports scenarios and does not choose, rank, approve, or reject a deal for the user.

## V21.7 — Negotiation Intelligence
- Transparent negotiation-price scenarios derived from explicit landed cost, target/minimum margin, selling commission and an explicit opening buffer.
- Calculates minimum acceptable price, target price, opening price and concession scenarios.
- Benchmark comparison is descriptive; no automatic recommendation, ranking or deal approval is made.
- Requires explicit FX and unit conversions.
- Endpoint: `POST /api/opportunities/{id}/negotiation-intelligence`.


## V21.8 — Opportunity Intelligence Dashboard
- `GET /api/opportunities/{opportunity_id}/intelligence`
- Aggregates buyer, demand, supplier, quotes, market benchmark, logistics scenarios, commercial offers and actions in one mobile-ready response.
- Preserves provenance/verification fields and explicitly treats Opportunity as an analytical lead, not a confirmed deal.
- Mobile RTL UI adds Opportunity Intelligence selector and chain-status visualization.

## V22.0 — Opportunity Operating System
- Pipeline stages: Discovered → Verified → Qualified → RFQ Sent → Supplier Quoted → Logistics Priced → Commercial Offer → Negotiation → Won/Lost.
- Stage ownership, due date, reason, loss reason, closure timestamp and stage audit trail.
- Evidence-aware stage transitions; the API rejects non-terminal transitions when required operational evidence is missing.
- Pipeline endpoint for mobile Kanban/list views with overdue and days-in-stage indicators.
- Operating-system endpoint for a single opportunity with stage, evidence, next stage and open work queue.
- APIs: `GET /api/opportunities/stages`, `GET /api/opportunities/pipeline`, `GET /api/opportunities/{id}/operating-system`, `POST /api/opportunities/{id}/stage`.

## V22.2 — Opportunity Health & Smart Scoring
- Live Opportunity Health score with explainable components: data quality, execution progress, speed, urgency, risk index.
- Buyer, supplier, demand, verification and product data-quality signals.
- Operational counts for quotes, routes, offers, RFQs, outbound communications, open/overdue actions.
- Health action recommendations endpoint.
- Mobile-first RTL dashboard card for Opportunity Health.
- Health is explicitly an operational/data-quality indicator, not a prediction of deal outcome.

### V22.2 endpoints
- `GET /api/opportunities/{id}/health`
- `GET /api/opportunities/health`
- `GET /api/opportunities/{id}/health/actions`

## V22.4 — Smart Data Quality & Verification Center
- Opportunity-level quality checklist for Buyer, Supplier, Demand and Product.
- Verification/evidence completeness and source URL quality.
- Commercial completeness for quotes, logistics, offers, RFQs and communications.
- Blocking vs warning findings and an explicit stage-advance gate.
- Endpoints: `/api/data-quality/opportunities`, `/api/opportunities/{id}/data-quality`, `/api/opportunities/{id}/data-quality/gate`.
- Quality is descriptive and does not predict deal outcome.

## V22.4 — Source & Evidence Intelligence
- Evidence Chain per Buyer/Supplier/Demand
- Source trust and freshness weighting
- Independent source/domain diversity
- Explicit claim conflict detection when evidence details contain `claim_key`/`claim_value` (or field/value)
- Verification history timeline
- Opportunity-level evidence score and recommendations
- APIs: `/api/opportunities/{id}/source-intelligence`, `/api/source-intelligence/opportunities`, `/api/opportunities/{id}/source-intelligence/conflicts`
- No source is treated as confirmation merely because it exists; conflicting or stale evidence remains visible for review.

## V22.5 — Temporal Market & Opportunity Intelligence
- Historical market-price trend analysis with explicit observation window.
- Freshness scoring for Buyer, Supplier, Demand, Verification and Market Benchmark.
- Opportunity stage aging and temporal health direction.
- Signals for stale evidence, stale benchmarks and changing market prices.
- APIs: `/api/opportunities/{id}/temporal-intelligence`, `/api/temporal-intelligence/opportunities`, `/api/market-prices/trend`.
- No outcome probability is inferred; temporal intelligence describes data freshness, movement and operational staleness.

## V22.6 — Cross-Source Change Detection
- Detects changed claims, cross-source conflicts, and changed source-record content hashes.
- Produces explainable change events without inventing facts.
- Optional persistence records `source_change_detected` AuditLog events with deterministic event hashes.
- Endpoints: `/api/opportunities/{id}/change-intelligence`, `/api/change-intelligence/opportunities`, `/api/opportunities/{id}/change-intelligence/audit`.
- Change detection is analytical; it does not infer deal outcomes.


## V22.8 — Intelligence Alert & Watchtower
- Health/Data Quality/Temporal/Change Detection signals are consolidated into actionable alerts.
- Watchtower supports dry-run planning, persistent alerts, deduplication, acknowledgement and resolution.
- APIs: `/api/watchtower/plan`, `/api/watchtower/run`, `/api/watchtower/alerts`, `/api/watchtower/alerts/{id}/acknowledge`, `/api/watchtower/alerts/{id}/resolve`.
- Alerts are operational signals, not predictions of deal success.


## V22.8 — Command Center & Executive Dashboard
- Unified executive summary API: `/api/command-center/summary`
- Operational opportunity queue: `/api/command-center/opportunities`
- Alert queue: `/api/command-center/alerts`
- Filters: market, product, stage, severity, status
- Aggregates Pipeline, Health, Data Quality, Verification, Alerts, actions, quotes, offers, routes, benchmarks and linked demands
- Mobile-first RTL dashboard with drill-down-oriented operational queue
- No new database table required; aggregation is derived from existing V22.7 intelligence data


## V23.1 — Country & Trade Rules Engine
- Country profiles for currencies, languages, payment methods and logistics nodes.
- Market-scoped trade rules with HS code/product scope, mandatory flag, verification status, documents, authority and source provenance.
- Effective-date filtering prevents expired/future rules from being treated as current.
- Trade-readiness endpoint summarizes recorded rules and verification blockers without inventing legal requirements.
- RBAC permissions: `market_rules.read` and `market_rules.write`.
- Migration: `0017_trade_rules`.

### Important
Regulatory/commercial requirements must be populated from authoritative sources and verified. The engine does not infer legal obligations merely because no rule has been entered.


## V23.3 — Import Cost & Duty Intelligence
- Structured, source-backed import-cost rules by Market + HS Code.
- Explicit duty, excise, VAT and other-fee bases; no legal rate is inferred.
- Only current `Verified` rules can calculate an import-cost result.
- Product and Opportunity endpoints resolve the verified HS classification first.
- Commercial Offer can explicitly apply the verified import-cost result to `customs_cost` with audit/provenance.
- No FX, freight or insurance is invented by the import-cost engine.
- Migration: `0019_import_cost_intelligence`.

## V23.4 — Landed Cost & Total Import Cost Intelligence
- Combines supplier, packaging, inland, export, freight, insurance, verified import taxes/fees, destination handling and other explicit costs into a traceable total landed cost.
- Prevents double-counting customs value: customs value is the tax base, while only the calculated import taxes/fees are added to landed cost.
- Explicit FX is required when currencies differ; no exchange rate is guessed.
- Calculations can be persisted with provenance to opportunity/commercial offer and linked Import Cost Rule / HS Code.
- APIs: `/api/opportunities/{id}/landed-cost`, `/api/opportunities/{id}/commercial-offers/{offer_id}/landed-cost`, `/api/opportunities/{id}/landed-cost` (GET history).
- Migration: `0020_landed_cost_intelligence`.

## V23.6.2 — Production Integrity & Mobile Deployment Hardening
- Fixed the Alembic revision chain so `0011_opportunity_operating_system` correctly follows `0010_market_price_intelligence`.
- Made the historical foreign-key alterations SQLite-compatible with Alembic batch operations, restoring the documented SQLite fallback.
- Centralized mutation RBAC enforcement so authenticated users cannot mutate business data outside their role permissions; read-only POST operations remain explicitly allowed.
- Added Watchtower write permission separation from Watchtower read access.
- Rate-limited setup and login endpoints in addition to authenticated API calls.
- Normalized SQLite session expiry timestamps to UTC before comparison.
- Production configuration now fails closed when the placeholder `SECRET_KEY` is used.
- Made pytest self-contained with `pythonpath = .`.
- Synchronized application/UI/service-worker versioning to `23.6.2`.
- Verified with Python compilation, JavaScript syntax checks, full unit suite, complete SQLite Alembic upgrade to head, and an authenticated smoke test.

### Current deployment target
Android PWA → GitHub → Railway Docker deployment → FastAPI → PostgreSQL.
The phone does not need Python, PostgreSQL, Docker, Passlib, or a local development environment.


## V24.16 operational controls
- External discovery uses persistent Search Cache, per-job/global/source/user request budgets, and durable DiscoveryJob records.
- Async discovery can be queued with `POST /api/discovery/jobs` and processed with `POST /api/discovery/jobs/{id}/run`. A dedicated worker is available via `python -m app.discovery.worker`.
- Readiness endpoint: `/api/readiness`.
- Production deployments should use PostgreSQL, a strong SECRET_KEY, explicit CORS origins, and a scheduled database backup/restore verification procedure.
- SQLite remains suitable for development/smoke tests only.
