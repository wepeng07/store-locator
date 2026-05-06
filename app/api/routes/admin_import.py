import csv
import io
from typing import Dict, Any, List, Tuple, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.deps import get_db
from app.core.rbac import require_store_manager
from app.models.store import Store
from app.services.geocoding import geocode_query

# 复用你 admin_stores.py 的 service 写入逻辑：建议抽到 app/services/store_services.py
# 这里为了让你“立刻能跑”，我直接从 admin_stores 引入函数（不优雅但可交付）
from app.api.routes.admin_stores import _set_store_services, ALLOWED_SERVICES  # noqa

router = APIRouter(prefix="/api/admin", tags=["admin-import"])


REQUIRED_HEADERS = [
    "store_id","name","store_type","status","latitude","longitude",
    "address_street","address_city","address_state","address_postal_code","address_country",
    "phone","services",
    "hours_mon","hours_tue","hours_wed","hours_thu","hours_fri","hours_sat","hours_sun"
]

STORE_TYPES = {"flagship", "regular", "outlet", "express"}
STATUSES = {"active", "inactive", "temporarily_closed"}
DAY_KEYS = ["mon","tue","wed","thu","fri","sat","sun"]


def _parse_float(val: str, field: str) -> Optional[float]:
    v = val.strip()
    if v == "":
        return None
    try:
        return float(v)
    except Exception:
        raise ValueError(f"{field} must be a number")


def _validate_lat_lon(lat: Optional[float], lon: Optional[float]) -> None:
    if lat is None or lon is None:
        return
    if not (-90 <= lat <= 90):
        raise ValueError("latitude out of range")
    if not (-180 <= lon <= 180):
        raise ValueError("longitude out of range")


def _normalize_phone(s: str) -> Optional[str]:
    s = (s or "").strip()
    return s if s else None


def _normalize_services_cell(cell: str) -> List[str]:
    """
    CSV services: "pharmacy|pickup|optical"
    """
    cell = (cell or "").strip()
    if cell == "":
        return []
    parts = [p.strip().lower() for p in cell.split("|") if p.strip() != ""]
    for p in parts:
        if p not in ALLOWED_SERVICES:
            raise ValueError(f"Invalid service: {p}")
    return sorted(set(parts))


def _validate_time_cell(v: str) -> str:
    """
    CSV hours cell: "08:00-22:00" or "closed"
    (We store as-is in a weekly map)
    """
    v = (v or "").strip().lower()
    if v == "":
        return "closed"
    if v == "closed":
        return "closed"
    import re
    m = re.match(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$", v)
    if not m:
        raise ValueError("hours must be HH:MM-HH:MM or closed")
    oh, om, ch, cm = map(int, m.groups())
    if (oh, om) >= (ch, cm):
        raise ValueError("hours open_time must be < close_time")
    return v


def _row_to_store_payload(row: Dict[str, str], auto_geocode: bool) -> Tuple[Dict[str, Any], List[str]]:
    """
    returns: (store_fields_dict, services_list)
    """
    store_id = row["store_id"].strip()
    if not store_id or not store_id.startswith("S"):
        raise ValueError("store_id invalid")

    store_type = row["store_type"].strip().lower()
    if store_type not in STORE_TYPES:
        raise ValueError("store_type invalid")

    status = row["status"].strip().lower()
    if status not in STATUSES:
        raise ValueError("status invalid")

    lat = _parse_float(row["latitude"], "latitude")
    lon = _parse_float(row["longitude"], "longitude")
    _validate_lat_lon(lat, lon)

    addr_street = row["address_street"].strip()
    addr_city = row["address_city"].strip()
    addr_state = row["address_state"].strip().upper()
    addr_zip = row["address_postal_code"].strip()
    addr_country = row["address_country"].strip().upper() or "USA"
    if not (addr_street and addr_city and addr_state and addr_zip and addr_country):
        raise ValueError("address fields missing")

    if auto_geocode and (lat is None or lon is None):
        q = f"{addr_street}, {addr_city}, {addr_state} {addr_zip}, {addr_country}"

        pass

    phone = _normalize_phone(row.get("phone", ""))

    services = _normalize_services_cell(row.get("services", ""))

    # hours: build weekly map from 7 columns
    weekly = {}
    for d in DAY_KEYS:
        weekly[d] = _validate_time_cell(row.get(f"hours_{d}", ""))

    import json
    hours_json_str = json.dumps({"timezone": "America/New_York", "weekly": weekly})

    store_fields = {
        "store_id": store_id,
        "name": row["name"].strip(),
        "store_type": store_type,
        "status": status,
        "latitude": lat,
        "longitude": lon,
        "address_street": addr_street,
        "address_city": addr_city,
        "address_state": addr_state,
        "address_postal_code": addr_zip,
        "address_country": addr_country,
        "phone": phone,
        "hours": hours_json_str,
    }
    return store_fields, services


@router.post("/stores/import", dependencies=[Depends(require_store_manager)])
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auto_geocode: bool = Query(default=True),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be .csv")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=400, detail="CSV must be utf-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    if headers != REQUIRED_HEADERS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "CSV headers must match required order and names",
                "expected": REQUIRED_HEADERS,
                "got": headers,
            },
        )

    rows = list(reader)
    if not rows:
        return {"total_rows": 0, "created": 0, "updated": 0, "failed": 0, "errors": []}

    report = {
        "total_rows": len(rows),
        "created": 0,
        "updated": 0,
        "failed": 0,
        "errors": [],  
    }

    try:
        for i, row in enumerate(rows, start=2):  # header is row 1
            store_id = (row.get("store_id") or "").strip()
            try:
                store_fields, services = _row_to_store_payload(row, auto_geocode=auto_geocode)

                if auto_geocode and (store_fields["latitude"] is None or store_fields["longitude"] is None):
                    q = f'{store_fields["address_street"]}, {store_fields["address_city"]}, {store_fields["address_state"]} {store_fields["address_postal_code"]}, {store_fields["address_country"]}'
                    lat, lon = await geocode_query(q)
                    store_fields["latitude"] = lat
                    store_fields["longitude"] = lon

                existing = db.query(Store).filter(Store.store_id == store_id).first()
                if existing:
                    for k, v in store_fields.items():
                        # store_id immutable
                        if k == "store_id":
                            continue
                        if hasattr(Store, k):
                            setattr(existing, k, v)
                    report["updated"] += 1
                else:
                    create_kwargs = {k: v for k, v in store_fields.items() if hasattr(Store, k)}
                    db.add(Store(**create_kwargs))
                    report["created"] += 1

                if services is not None:
                    _set_store_services(db, store_id, services)

            except Exception as e:
                report["failed"] += 1
                report["errors"].append({"row_number": i, "store_id": store_id, "error": str(e)})
                # all-or-nothing: raise to rollback whole transaction
                raise

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(status_code=422, detail=report)

    return report
