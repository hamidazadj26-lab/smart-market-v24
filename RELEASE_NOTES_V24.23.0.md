# SMART MARKET V24.23.0 — Interactive Commercial Intelligence Map

## Baseline comparison
- Compared the available V24.21.3 OSIRIS Integration archive with the newer V24.22.0 Trade Radar & OSIRIS archive.
- V24.22.0 is the newer base and preserves its evidence-aware Trade Radar and opt-in read-only OSIRIS adapter.
- The GeoJSON map service present in V24.21.3 was not present in V24.22.0, so the map service, authenticated endpoint, and tests were merged into the newer base rather than reverting to the older archive.

## Added in V24.23.0
- Authenticated `GET /api/intelligence/map.geojson` endpoint, filtered by selected layers, country, map bounds, and bounded result limit.
- Strict WGS84 coordinate validation, source/provenance fields, confidence normalization, no inferred/geocoded coordinates, antimeridian-aware bounds, and explicit truncation metadata.
- Persian RTL interactive map view in the existing mobile-first portal using Leaflet; manufacturer, customer, and demand layers can be toggled.
- Map markers show record details, verification state, confidence, observation time, and safe HTTP(S)-only source links.
- Map bounds trigger bounded refreshes; a compact record list lets users focus the map on an item.
- PWA cache version bumped to 24.23.0; app runtime version bumped to 24.23.0.
- Smoke test now creates sample records with stored coordinates and verifies the authenticated map endpoint returns GeoJSON.

## Guardrails and limits
- No location is inferred from city/address strings; records without valid stored coordinates are omitted from the map.
- No new database migration was required.
- Leaflet is loaded from a public CDN when the map view is opened. If that CDN is unreachable, the map view reports the failure instead of breaking the rest of the portal.
- The default OpenStreetMap tile endpoint is suitable only subject to its published usage policy and capacity. Before high-volume commercial production, choose a tile provider/service with terms and capacity appropriate to expected traffic; keep visible attribution.
- Browser interaction with external tile/CDN providers and live Railway deployment were not tested here.
- No GitHub repository or Railway deployment was modified.

## Verification
- `pytest -q`: 159 passed, 2 skipped.
- `python -m compileall -q app tests`: passed.
- `node --check static/app.js`: passed.
- `python smoke_test.py`: passed; migration chain reached revision 0040 and map endpoint returned GeoJSON with two or more sample records.
