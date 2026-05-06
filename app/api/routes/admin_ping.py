from fastapi import APIRouter, Depends

from app.core.rbac import require_store_reader, require_store_manager, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/ping", dependencies=[Depends(require_store_reader)])
def ping_reader():
    return {"ok": True, "scope": "reader"}

@router.post("/ping", dependencies=[Depends(require_store_manager)])
def ping_manager():
    return {"ok": True, "scope": "manager"}

@router.delete("/ping", dependencies=[Depends(require_admin)])
def ping_admin():
    return {"ok": True, "scope": "admin"}
