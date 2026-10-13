# Audit & Change Report — SMART MARKET V24.23.0

## Executive summary
The latest available candidate found in the working Library was `SMART_MARKET_V24.22.0_TRADE_RADAR_OSIRIS.zip`, newer than the attached/local V24.21.3 archive. Development continued from V24.22.0 to preserve the existing Trade Radar and optional OSIRIS context adapter. The map API/service from V24.21.3 was then merged into that newer base, and a Persian mobile-first interactive map view was added.

## Version comparison
### Preserved from V24.22.0
- Evidence-aware Trade Radar, with stored opportunities separated from discovery candidates.
- Read-only OSIRIS context adapter, disabled by default and restricted to an allowlist of feeds.
- Existing land-cost, route, quote, trade optimizer, evidence, verification, temporal intelligence, and Watchtower features.

### Recovered from V24.21.3
- `app/services/intelligence_map.py` and the authenticated `GET /api/intelligence/map.geojson` endpoint.
- Coordinate validation, source provenance, confidence handling, bounding-box filters, and result caps.
- Map unit tests for invalid coordinates, provenance, antimeridian bounds, and truncation.

### Added in V24.23.0
- Interactive Leaflet map launched from the dashboard.
- Toggleable manufacturer/customer/demand layers; country filter; viewport-based API requests; safe popups and source links; focus-on-record controls.
- PWA service-worker cache and runtime version bumped to 24.23.0.
- Smoke test coverage for the authenticated map endpoint using explicit test coordinates.

## Files changed
- `app/config.py`
- `app/routers/intelligence.py`
- `app/services/intelligence_map.py` (new)
- `static/app.js`
- `static/styles.css`
- `static/index.html`
- `static/sw.js`
- `tests/test_intelligence_map.py` (new)
- `tests/test_mobile_contract.py`
- `smoke_test.py`
- `README.md`
- `RELEASE_NOTES_V24.23.0.md` (new)

## Test results
- Full pytest suite: **159 passed, 2 skipped, 0 failed**.
- Python compile check: passed.
- JavaScript syntax check: passed.
- End-to-end local smoke test: passed; migrations applied through `0040_commercial_offer_fx_provenance`; setup/login/dashboard/product/manufacturer/customer/demand/discovery/rebuild/trade-radar/map/OSIRIS-disabled/logout paths exercised.
- Archive integrity (`ZipFile.testzip`) verified after packaging.

## Important limitations
- The map UI was syntax-checked and backend-smoke-tested, but not exercised in a real browser session or Android WebView in this environment.
- External CDN loading and map tile rendering were not tested. Leaflet is loaded on demand, so failure is isolated to the map view. OpenStreetMap's standard tile service has a published usage policy and no production SLA; select a suitable provider before commercial scale.
- Live OSIRIS feeds remain opt-in and were not contacted during tests.
- No live PostgreSQL/Redis production environment, Railway deployment, or GitHub push was performed.
- Scores in the Trade Radar remain prioritization heuristics, not calibrated probabilities of a successful sale.

## External mapping references
- Leaflet Quick Start: https://leafletjs.com/examples/quick-start/
- OpenStreetMap tile usage policy: https://operations.osmfoundation.org/policies/tiles/

## Deployment caution
Do not overwrite a newer live GitHub repository blindly. Compare this archive against the current repository head and preserve any newer user edits before upload. After deployment, validate `/api/health`, login, `GET /api/intelligence/map.geojson`, and browser tile rendering.
