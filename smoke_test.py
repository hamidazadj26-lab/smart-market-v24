"""Isolated smoke test: creates a temporary SQLite database and removes it afterward."""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="smart-market-smoke-") as tmp:
    db_path = Path(tmp) / "smoke_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["SECRET_KEY"] = "test-secret-please-change"

    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=os.environ.copy())
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    r = c.get("/api/setup/status")
    assert r.status_code == 200 and r.json()["setup_required"] is True
    r = c.post("/api/setup", json={"username": "admin", "password": "strong-password-123"})
    assert r.status_code == 200
    r = c.post("/api/login", json={"username": "admin", "password": "strong-password-123"})
    assert r.status_code == 200
    r = c.get("/api/dashboard")
    assert r.status_code == 200
    r = c.post("/api/products", json={"name": "رزین اپوکسی"})
    assert r.status_code == 200
    pid = r.json()["id"]
    r = c.post("/api/manufacturers", json={"name": "تولیدکننده آزمایشی", "product_id": pid, "city": "تهران", "capacity_value": 20, "capacity_unit": "ton", "confidence": 0.9})
    assert r.status_code == 200
    r = c.post("/api/customers", json={"name": "مشتری آزمایشی", "country": "Afghanistan", "city": "Herat", "product_id": pid})
    assert r.status_code == 200
    r = c.post("/api/demands", json={"product_id": pid, "quantity": 10, "unit": "ton", "country": "Afghanistan", "city": "Herat", "verification_status": "Verified"})
    assert r.status_code == 200
    r = c.post("/api/discovery/run", json={"product": "epoxy resin", "texts": ["Company: Example Trading Ltd needs to purchase epoxy resin in Herat Afghanistan"]})
    assert r.status_code == 200 and r.json()["processed"] == 1
    r = c.post("/api/opportunities/rebuild")
    assert r.status_code == 200
    r = c.get("/api/opportunities")
    assert r.status_code == 200
    r = c.post("/api/logout")
    assert r.status_code == 200
    print("SMOKE OK")
