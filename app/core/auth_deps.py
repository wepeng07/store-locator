from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.jwt_utils import decode_token

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_claims(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = creds.credentials
    try:
        claims = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # basic shape check
    for k in ("user_id", "email", "role"):
        if k not in claims:
            raise HTTPException(status_code=401, detail="Invalid token payload")

    return claims
