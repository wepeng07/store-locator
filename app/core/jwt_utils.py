import os
import time
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt
from app.core.config import settings 

JWT_SECRET = settings.JWT_SECRET_KEY
JWT_ALG = settings.JWT_ALGORITHM
ACCESS_MIN = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(payload: Dict[str, Any]) -> str:
    exp = _now_utc() + timedelta(minutes=ACCESS_MIN)
    to_encode = dict(payload)
    to_encode["exp"] = int(exp.timestamp())
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)


def create_refresh_token(payload: Dict[str, Any]) -> str:
    exp = _now_utc() + timedelta(days=REFRESH_DAYS)
    to_encode = dict(payload)
    to_encode["exp"] = int(exp.timestamp())
    # refresh token 带一个 jti，方便审计（可选）
    to_encode["jti"] = str(uuid.uuid4())
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


def refresh_expiry_utc() -> datetime:
    return _now_utc() + timedelta(days=REFRESH_DAYS)
