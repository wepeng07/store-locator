from fastapi import Depends, HTTPException

from app.core.auth_deps import get_current_claims

ROLE_ADMIN = "admin"
ROLE_MARKETER = "marketer"
ROLE_VIEWER = "viewer"

def require_roles(*allowed_roles: str):
    def _dep(claims=Depends(get_current_claims)):
        role = claims.get("role")
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return claims
    return _dep

# convenience
require_admin = require_roles(ROLE_ADMIN)
require_store_manager = require_roles(ROLE_ADMIN, ROLE_MARKETER)  # can create/update/deactivate
require_store_reader = require_roles(ROLE_ADMIN, ROLE_MARKETER, ROLE_VIEWER)  # read-only
