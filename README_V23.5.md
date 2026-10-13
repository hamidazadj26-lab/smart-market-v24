# SMART MARKET V23.5

## Trade Route & Border Cost Intelligence

Adds explicit trade-route profiles, ordered route segments, border/port/transit/destination costs, currency normalization with explicit FX rates, route calculations, provenance fields, audit events, and calculation history.

### Endpoints
- GET/POST `/api/opportunities/{opportunity_id}/trade-routes`
- POST `/api/opportunities/{opportunity_id}/trade-routes/{route_id}/segments`
- POST `/api/opportunities/{opportunity_id}/trade-routes/{route_id}/calculate`
- GET `/api/opportunities/{opportunity_id}/trade-routes/{route_id}/calculations`

### Safety of calculations
No route, freight, border fee, transit cost, FX rate, or timing is inferred. Currency conversion requires explicit FX rates when currencies differ. Every route and segment has verification/source fields.
