# SMART MARKET V24.22.0 — Trade Radar & OSIRIS Context Adapter

## Added
- Evidence-aware trade radar endpoint: `GET /api/intelligence/trade-radar`.
- Separate rankings for existing commercial opportunities and unlinked discovery candidates.
- Explanations for score composition and score coverage; next-action recommendations based on evidence completeness, verification, source availability, and conflicts.
- Mobile-first dashboard button for the Trade Radar view, with source links restricted to HTTP(S).
- Optional read-only OSIRIS adapter for `country_risk`, `maritime`, and `gdelt` feeds via `GET /api/intelligence/osiris-context`.
- OSIRIS configuration is opt-in and disabled by default; no database writes occur from the OSIRIS endpoint.
- Tests for score coverage, confidence normalization, empty datasets, traceable candidate records, feed allowlisting, and URL validation.
- Fixed an existing opportunity-rebuild bug that referenced the distance variable before assignment; smoke test now covers Trade Radar and disabled OSIRIS behavior.

## Guardrails
- Discovery candidates are not presented as verified buyers or confirmed orders.
- OSIRIS feed data is contextual and is not converted into commercial evidence automatically.
- No unverified FX, freight, customs, buyer, or price values are inferred.
- No database migration is required; existing V24.21.2 schema is reused.

## Verification performed
- `pytest -q`: 152 passed, 2 skipped.
- `node --check static/app.js`: passed.
- `python -m compileall -q app tests`: passed.
- Live external OSIRIS feed integration was not tested as part of this local verification.
- GitHub repository was not modified; the linked private repository returned HTTP 404 to the connected GitHub integration in this session.
