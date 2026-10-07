# SMART MARKET V23.6.2

## End-to-End Trade Cost & Route Optimizer

V23.6 adds a transparent Supplier Quote × Trade Route scenario engine. It compares every selected supplier quote against every selected trade route, normalizes currencies only with explicit FX rates, optionally adds verified import taxes only when an explicit customs value is supplied, persists calculation runs/results, and can create a Commercial Offer from a selected result.

### Double-counting protection
When a Trade Route is selected, Supplier Quote freight is not added again. Route segment costs are the logistics component. Import taxes are added only from a current verified ImportCostRule and an explicit customs value.

### API
- `POST /api/opportunities/{id}/trade-optimizer`
- `GET /api/opportunities/{id}/trade-optimizer/runs`
- `GET /api/opportunities/{id}/trade-optimizer/runs/{run_id}`
- `POST /api/opportunities/{id}/trade-optimizer/apply`

### Migration
`0022_trade_optimization`

### Validation
The V23.6 focused suite covers the optimizer, route calculation, landed cost and import cost modules. Full production runtime validation still depends on the deployment environment and installed dependencies.
