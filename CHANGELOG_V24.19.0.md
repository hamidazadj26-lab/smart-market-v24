# SMART MARKET V24.19.0 — Intelligence Integrity Fix Pack

## تکمیل‌های این نسخه
- اتصال `Opportunity` به موجودیت‌های canonical `Supplier` و `Buyer` با migration `0039_opportunity_canonical_actors`.
- ایجاد/حل canonical Supplier و Buyer هنگام rebuild فرصت‌ها برای جلوگیری از دوگانگی Manufacturer/Customer و actor intelligence.
- API مستقل برای فهرست و ثبت Supplier و Buyer canonical.
- Central Commercial Fact API با الزام provenance از `SourceSignal` یا `VerificationEvidence`.
- FX Rate API با الزام منبع و endpoint برای آخرین نرخ معتبر و منقضی‌نشده.
- AI Inference provenance API با ثبت model/model_version/generated_at/confidence/evidence_ids.
- اصلاح mutable defaults در چند ورودی Pydantic حساس.
- به‌روزرسانی نسخه frontend/service worker به V24.19.0.

## اعتبارسنجی
- `python -m compileall -q app migrations scripts` → PASS
- `pytest -q` → **126 passed, 2 skipped**
- Alembic upgrade روی SQLite → **0039_opportunity_canonical_actors** موفق
- Smoke test موجود پروژه → **SMOKE OK**
- API smoke برای canonical Supplier/Buyer → **PASS**

## محدودیت‌های عمداً باقی‌مانده
- PostgreSQL و Redis واقعی در این محیط در دسترس نیستند؛ بنابراین تست integration واقعی آن‌ها هنوز انجام نشده است.
- این نسخه به Railway متصل/Deploy نشده است.
- GitHub target هنوز باید با همین artifact به‌صورت واقعی commit و verify شود.
