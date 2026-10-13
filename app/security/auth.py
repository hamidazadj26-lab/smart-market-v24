import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from sqlalchemy.orm import Session
from fastapi import HTTPException, Request
from ..models import Admin, SessionToken
from ..config import get_settings

# Argon2id is used directly so authentication has no Passlib dependency.
pwd = PasswordHasher()


def hash_password(password: str) -> str:
    return pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def issue_session(db: Session, admin: Admin):
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    session = SessionToken(
        admin_id=admin.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=get_settings().session_ttl_hours),
    )
    db.add(session)
    db.commit()
    return raw


def get_admin(request: Request, db: Session):
    raw = request.cookies.get('sm_session')
    if not raw:
        raise HTTPException(401, 'احراز هویت لازم است.')
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    session = db.query(SessionToken).filter(
        SessionToken.token_hash == token_hash,
        SessionToken.revoked_at.is_(None),
    ).first()
    if not session:
        raise HTTPException(401, 'نشست منقضی یا نامعتبر است.')
    expires_at=session.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at=expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(401, 'نشست منقضی یا نامعتبر است.')
    admin = db.get(Admin, session.admin_id)
    if not admin or not admin.is_active:
        raise HTTPException(401, 'کاربر غیرفعال است.')
    return admin


def revoke_session(db: Session, request: Request):
    raw = request.cookies.get('sm_session')
    if raw:
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        session = db.query(SessionToken).filter(SessionToken.token_hash == token_hash).first()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
