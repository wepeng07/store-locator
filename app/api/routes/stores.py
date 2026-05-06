from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Any

from app.db.deps import get_db
from app.services.store_search import search_method2
from app.services.geocoding import geocode_query
from app.services.store_services import get_services_for_store_ids
from app.utils.open_now import is_open_now
from app.services.search_cache import make_key, get_cached, set_cached

router = APIRouter()


class SearchRequest(BaseModel):
    address: Optional[str] = None
    postal_code: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    radius_miles: float = Field(default=10, ge=0.1, le=100)

    services: Optional[List[str]] = None
    store_types: Optional[List[str]] = None
    open_now: Optional[bool] = None


def _clean_list(vals: Optional[List[str]]) -> List[str]:
    if not vals:
        return []
    out = []
    for v in vals:
        if v is None:
            continue
        if not isinstance(v, str):
            continue
        t = v.strip().lower()
        if t:
            out.append(t)
    return out


def _normalize_pairs(pairs: List[Any]) -> List[Tuple[float, Any]]:
    """
    Normalize search_method2 results to List[(dist_miles, Store)].

    Accept (common cases):
      - (dist, store)
      - (store, dist)
      - (dist, store, extra...)
      - store only  -> dist=0.0 (fallback)
    """
    out: List[Tuple[float, Any]] = []
    for item in pairs or []:
        # tuple/list
        if isinstance(item, (list, tuple)):
            if len(item) >= 2:
                a, b = item[0], item[1]
                # detect which side is distance
                if isinstance(a, (int, float)) and not isinstance(b, (int, float)):
                    out.append((float(a), b))
                elif isinstance(b, (int, float)) and not isinstance(a, (int, float)):
                    out.append((float(b), a))
                else:
                    # fallback assume (dist, store)
                    try:
                        out.append((float(a), b))
                    except Exception:
                        out.append((0.0, b))
            elif len(item) == 1:
                out.append((0.0, item[0]))
            else:
                continue
        else:
            # store only
            out.append((0.0, item))
    return out


@router.post("/api/stores/search")
async def search(req: SearchRequest, db=Depends(get_db)):
    # -------- 1) Resolve input -> coordinates --------
    if req.lat is not None and req.lon is not None:
        search_lat, search_lon = req.lat, req.lon
        input_type = "coordinates"
        input_value = {"lat": req.lat, "lon": req.lon}

    elif req.address is not None:
        try:
            search_lat, search_lon = await geocode_query(req.address)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Geocoding failed: {repr(e)}")
        input_type = "address"
        input_value = req.address

    elif req.postal_code is not None:
        try:
            query = f"{req.postal_code}, USA"
            search_lat, search_lon = await geocode_query(query)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Geocoding failed: {repr(e)}")
        input_type = "postal_code"
        input_value = req.postal_code

    else:
        raise HTTPException(status_code=400, detail="Provide either lat+lon, address, or postal_code")

    services_clean = _clean_list(req.services)
    store_types_clean = _clean_list(req.store_types)

    # -------- 2) Cache lookup --------
    cache_payload = {
        "search_lat": round(float(search_lat), 6),
        "search_lon": round(float(search_lon), 6),
        "radius_miles": float(req.radius_miles),
        "services": sorted(services_clean),
        "store_types": sorted(store_types_clean),
        "open_now": req.open_now,
        "input": {"type": input_type, "value": input_value},
    }
    ckey = make_key(cache_payload)
    cached = get_cached(ckey)
    if cached is not None:
        return JSONResponse(content=cached, headers={"X-Cache": "HIT"})

    # -------- 3) DB search (method2) --------
    raw_pairs = search_method2(
        db,
        search_lat,
        search_lon,
        req.radius_miles,
        limit=20,
        store_types=store_types_clean or None,
        services=services_clean or None,
    )
    pairs = _normalize_pairs(raw_pairs)

    # -------- 4) services map (many-to-many) --------
    store_ids = [store.store_id for dist, store in pairs]
    services_map = get_services_for_store_ids(db, store_ids) if store_ids else {}

    applied_filters = {
        "radius_miles": float(req.radius_miles),
        "services": services_clean,
        "store_types": store_types_clean,
        "open_now": req.open_now,
    }

    # -------- 5) open_now filter (IMPORTANT) --------
    filtered: List[Tuple[float, Any, Optional[bool]]] = []
    for dist, store in pairs:
        open_state = is_open_now(getattr(store, "hours", None))
        if req.open_now is None:
            filtered.append((dist, store, open_state))
        else:
            # must be known and match
            if open_state is None:
                continue
            if open_state == req.open_now:
                filtered.append((dist, store, open_state))

    # -------- 6) response build (USE filtered, not pairs) --------
    response = {
        "searched_location": {"lat": float(search_lat), "lon": float(search_lon)},
        "radius_miles": float(req.radius_miles),
        "input": {"type": input_type, "value": input_value},
        "applied_filters": applied_filters,
        "count": len(filtered),
        "results": [
            {
                "store": {
                    "id": store.store_id,
                    "name": store.name,
                    "address": {
                        "street": store.address_street,
                        "city": store.address_city,
                        "state": store.address_state,
                        "postal_code": store.address_postal_code,
                        "country": store.address_country,
                    },
                    "type": store.store_type,
                    "services": services_map.get(store.store_id, []),
                    "phone": getattr(store, "phone", None),
                    "hours": getattr(store, "hours", None),
                    "status": store.status,
                },
                "distance_miles": round(float(dist), 3),
                "is_open_now": open_state,
            }
            for dist, store, open_state in filtered
        ],
    }

    # -------- 7) Cache set --------
    set_cached(ckey, response)
    return JSONResponse(content=response, headers={"X-Cache": "MISS"})
