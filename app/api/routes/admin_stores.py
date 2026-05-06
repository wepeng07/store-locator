from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.deps import get_db
from app.core.rbac import require_store_reader, require_store_manager
from app.models.store import Store
from app.models.service import Service
from app.models.store_service import StoreService
from app.services.geocoding import geocode_query

router = APIRouter(prefix="/api/admin", tags=["admin-stores"])


StoreType = Literal["flagship", "regular", "outlet", "express"]
StoreStatus = Literal["active", "inactive", "temporarily_closed"]

ALLOWED_SERVICES = {
    "pharmacy", "pickup", "returns", "optical", "photo_printing",
    "gift_wrapping", "automotive", "garden_center"
}


class StoreCreateReq(BaseModel):
    store_id: str = Field(..., pattern=r"^S\d{4}$")
    name: str
    store_type: StoreType
    status: StoreStatus = "active"

    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    address_street: str
    address_city: str
    address_state: str = Field(..., min_length=2, max_length=2)
    address_postal_code: str = Field(..., min_length=5, max_length=10)
    address_country: str = Field(default="USA", min_length=3, max_length=3)

    phone: Optional[str] = None

    services: Optional[List[str]] = None
    hours: Optional[str] = None 


class StorePatchReq(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    services: Optional[List[str]] = None
    status: Optional[StoreStatus] = None
    hours: Optional[str] = None


def _get_services_map(db: Session, store_ids: List[str]) -> dict[str, List[str]]:
    rows = (
        db.query(StoreService.store_id, StoreService.service_name)
        .filter(StoreService.store_id.in_(store_ids))
        .all()
    )
    m: dict[str, List[str]] = {}
    for sid, sname in rows:
        m.setdefault(sid, []).append(sname)
    for sid in m:
        m[sid].sort()
    return m


def _store_to_dict(store: Store, services: List[str]):
    return {
        "store_id": store.store_id,
        "name": store.name,
        "store_type": store.store_type,
        "status": store.status,
        "latitude": store.latitude,
        "longitude": store.longitude,
        "address": {
            "street": store.address_street,
            "city": store.address_city,
            "state": store.address_state,
            "postal_code": store.address_postal_code,
            "country": store.address_country,
        },
        "phone": getattr(store, "phone", None),
        "services": services,
        "hours": getattr(store, "hours", None),
    }


def _validate_services(services: List[str]) -> List[str]:
    cleaned = []
    for s in services:
        if not isinstance(s, str):
            raise HTTPException(status_code=422, detail="services must be list of strings")
        val = s.strip().lower()
        if val not in ALLOWED_SERVICES:
            raise HTTPException(status_code=422, detail=f"Invalid service: {val}")
        cleaned.append(val)
    return sorted(set(cleaned))


def _set_store_services(db: Session, store_id: str, services: List[str]) -> None:
    """
    Replace store services with provided list (full replace).
    """
    services = _validate_services(services)

    existing = {name for (name,) in db.query(Service.name).filter(Service.name.in_(services)).all()}
    for name in services:
        if name not in existing:
            db.add(Service(name=name))

    # delete old
    db.query(StoreService).filter(StoreService.store_id == store_id).delete()

    # insert new
    for name in services:
        db.add(StoreService(store_id=store_id, service_name=name))


# ---------- Endpoints ----------
@router.post("/stores", dependencies=[Depends(require_store_manager)])
async def create_store(req: StoreCreateReq, db: Session = Depends(get_db)):
    lat = req.latitude
    lon = req.longitude

    # auto-geocode if missing coords
    if lat is None or lon is None:
        q = f"{req.address_street}, {req.address_city}, {req.address_state} {req.address_postal_code}, {req.address_country}"
        try:
            lat, lon = await geocode_query(q)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Geocoding failed: {e}")

    store = Store(
        store_id=req.store_id,
        name=req.name,
        store_type=req.store_type,
        status=req.status,
        latitude=lat,
        longitude=lon,
        address_street=req.address_street,
        address_city=req.address_city,
        address_state=req.address_state,
        address_postal_code=req.address_postal_code,
        address_country=req.address_country,
    )
    # optional columns
    if hasattr(Store, "phone"):
        store.phone = req.phone
    if hasattr(Store, "hours"):
        store.hours = req.hours

    db.add(store)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="store_id already exists")

    if req.services is not None:
        _set_store_services(db, req.store_id, req.services)
        db.commit()

    services_map = _get_services_map(db, [req.store_id])
    return _store_to_dict(store, services_map.get(req.store_id, []))


@router.get("/stores", dependencies=[Depends(require_store_reader)])
def list_stores(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    q = db.query(Store).order_by(Store.store_id).limit(limit).offset(offset)
    stores = q.all()
    ids = [s.store_id for s in stores]
    services_map = _get_services_map(db, ids) if ids else {}
    return {
        "limit": limit,
        "offset": offset,
        "count": len(stores),
        "results": [_store_to_dict(s, services_map.get(s.store_id, [])) for s in stores],
    }


@router.get("/stores/{store_id}", dependencies=[Depends(require_store_reader)])
def get_store(store_id: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    services_map = _get_services_map(db, [store_id])
    return _store_to_dict(store, services_map.get(store_id, []))


@router.patch("/stores/{store_id}", dependencies=[Depends(require_store_manager)])
def patch_store(store_id: str, req: StorePatchReq, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    data = req.model_dump(exclude_unset=True)

    if "name" in data:
        store.name = data["name"]

    if "phone" in data:
        if not hasattr(Store, "phone"):
            raise HTTPException(status_code=400, detail="phone column not available in Store model")
        store.phone = data["phone"]

    if "status" in data:
        store.status = data["status"]

    if "hours" in data:
        if not hasattr(Store, "hours"):
            raise HTTPException(status_code=400, detail="hours column not available in Store model")
        store.hours = data["hours"]

    if "services" in data:
        _set_store_services(db, store_id, data["services"])

    db.commit()

    services_map = _get_services_map(db, [store_id])
    return _store_to_dict(store, services_map.get(store_id, []))


@router.delete("/stores/{store_id}", dependencies=[Depends(require_store_manager)])
def deactivate_store(store_id: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    store.status = "inactive"
    db.commit()

    services_map = _get_services_map(db, [store_id])
    return _store_to_dict(store, services_map.get(store_id, []))
