# SMART MARKET V24.20.0 — Production Integrity Fix Pack

- رفع تعریف تکراری مسیر GET `/api/market-prices/trend`.
- یکسان‌سازی نسخه backend/frontend/service worker روی V24.20.0.
- افزودن آزمون جلوگیری از ثبت دوباره مسیر بازار.
- CI اکنون migration واقعی PostgreSQL را با `alembic upgrade head` و `alembic check` اعتبارسنجی می‌کند.
