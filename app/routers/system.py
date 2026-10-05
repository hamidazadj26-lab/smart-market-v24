"""System/authentication routes extracted from the legacy monolithic API.

V24 migration slice: behavior and public API paths are intentionally unchanged.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings

router = APIRouter(tags=["system"])
settings = get_settings()

from ..database import get_db
from ..models import Admin
from ..schemas import LoginIn, SetupIn
from ..security.auth import hash_password, issue_session, revoke_session, verify_password
from ..services.request_guard import enforce_rate_limit
from ..services.health import check_database, check_redis, check_worker, check_migrations

@router.get("/api/live")
def liveness():
    """Process liveness: no external dependency is required."""
    return {"status": "alive", "version": settings.version}


@router.get("/api/readiness")
def readiness():
    """API readiness checks only dependencies required to serve requests."""
    checks = {}
    db_ok, db_detail = check_database()
    redis_ok, redis_detail = check_redis()
    migration_ok, migration_detail = check_migrations()
    checks["database"] = {"status": "ok" if db_ok else "error", "detail": db_detail}
    checks["redis"] = {"status": "ok" if redis_ok else "error", "detail": redis_detail}
    checks["migrations"] = {"status": "ok" if migration_ok else "error", "detail": migration_detail}
    production = settings.environment.lower() == "production"
    critical = (db_ok and redis_ok and migration_ok) if production else db_ok
    payload = {"status": "ready" if critical else "not_ready", "version": settings.version, "environment": settings.environment, "checks": checks}
    if not critical:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=payload)
    return payload


@router.get("/api/health")
def health():
    checks = {}
    db_ok, db_detail = check_database()
    redis_ok, redis_detail = check_redis()
    migration_ok, migration_detail = check_migrations()
    worker_ok, worker_detail = check_worker()
    checks["database"] = {"status": "ok" if db_ok else "error", "detail": db_detail}
    checks["redis"] = {"status": "ok" if redis_ok else "error", "detail": redis_detail}
    checks["migrations"] = {"status": "ok" if migration_ok else "error", "detail": migration_detail}
    checks["worker"] = {"status": "ok" if worker_ok else "error", "detail": worker_detail}
    production = settings.environment.lower() == "production"
    # Worker health is reported but is not an API readiness dependency; otherwise
    # a worker-only failure could cause the API service to restart unnecessarily.
    healthy = (db_ok and redis_ok and migration_ok) if production else db_ok
    payload = {"status": "ok" if healthy else "degraded", "version": settings.version, "environment": settings.environment, "checks": checks, "worker_degraded": not worker_ok}
    if not healthy:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=payload)
    return payload


@router.get("/api/setup/status")
def setup_status(db: Session = Depends(get_db)):
    return {"setup_required": db.query(Admin).count() == 0}


@router.post("/api/setup")
def setup(data: SetupIn, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(request)
    if db.query(Admin).count():
        raise HTTPException(409, "Setup قبلاً انجام شده است.")
    admin = Admin(
        username=data.username.strip(),
        password_hash=hash_password(data.password),
        role="Super Admin",
    )
    db.add(admin)
    db.commit()
    return {"status": "ok"}


@router.post("/api/login")
def login(
    data: LoginIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request)
    admin = db.query(Admin).filter(Admin.username == data.username).first()
    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(401, "نام کاربری یا رمز عبور نادرست است.")
    raw = issue_session(db, admin)
    response.set_cookie(
        "sm_session",
        raw,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=settings.session_ttl_hours * 3600,
    )
    return {"status": "ok", "username": admin.username}


@router.post("/api/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    # Logout is public to allow expired/invalid sessions to be cleared, but it
    # still touches the database and therefore must be rate-limited.
    enforce_rate_limit(request)
    revoke_session(db, request)
    response.delete_cookie("sm_session")
    return {"status": "ok"}
