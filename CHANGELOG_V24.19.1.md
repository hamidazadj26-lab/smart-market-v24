# SMART MARKET V24.19.1

## Remaining-defect fix

- Fixed stale mobile contract test that still expected V24.18.0 after the frontend moved to V24.19.0.
- Updated visible frontend version labels from V24.18 to V24.19.
- Fixed canonical Supplier/Buyer identity resolution when source-backed phone/website fields change. The system now attempts stable name + country + city resolution before creating a duplicate canonical actor and then refreshes the canonical key.
- Added regression coverage for canonical actor synchronization.

## Verification

- pytest: 127 passed, 2 skipped (PostgreSQL/Redis integration tests require external services).
- compileall: passed.
- Alembic migration chain: single head 0039.
- smoke_test.py: SMOKE OK.
