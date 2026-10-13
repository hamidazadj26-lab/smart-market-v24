
## V22.1 — Automation & Follow-up Engine
- Idempotent automation creates `OpportunityAction` records for overdue stages, due-within-24h stages, missing follow-up for `next_action`, and stale stages without explicit due dates.
- Dry-run planning: `GET /api/automation/plan`.
- Execute automation: `POST /api/automation/run` with optional `opportunity_id` and `dry_run`.
- Overdue queue: `GET /api/automation/overdue`.
- No background thread is required; deployment schedulers can call the run endpoint safely because markers prevent duplicate open actions.
- Terminal Won/Lost opportunities and archived opportunities are excluded.
