import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.passwords import verify_password
from app.core.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    refresh_expiry_utc,
)

router = APIRouter(tags=["auth"])


class LoginReq(BaseModel):
    email: str
    password: str


class LoginResp(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshReq(BaseModel):
    refresh_token: str


class LogoutReq(BaseModel):
    refresh_token: str


@router.post("/api/auth/login", response_model=LoginResp)
def login(req: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {"user_id": user.user_id, "email": user.email, "role": user.role}

    access = create_access_token(payload)
    refresh = create_refresh_token(payload)

    rt = RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user.user_id,
        token_hash=hash_token(refresh),
        revoked=False,
        expires_at=refresh_expiry_utc(),
        created_at=datetime.utcnow(),
    )
    db.add(rt)
    db.commit()

    return LoginResp(access_token=access, refresh_token=refresh)


@router.post("/api/auth/refresh")
def refresh(req: RefreshReq, db: Session = Depends(get_db)):
    try:
        claims = decode_token(req.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    h = hash_token(req.refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == h).first()
    if not rt or rt.revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked/unknown")

    if rt.expires_at and rt.expires_at < datetime.now(rt.expires_at.tzinfo):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    payload = {"user_id": claims["user_id"], "email": claims["email"], "role": claims["role"]}
    new_access = create_access_token(payload)
    return {"access_token": new_access, "token_type": "bearer"}


@router.post("/api/auth/logout")
def logout(req: LogoutReq, db: Session = Depends(get_db)):
    h = hash_token(req.refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == h).first()
    if not rt:
        return {"ok": True}
    rt.revoked = True
    db.commit()
    return {"ok": True}
