from app.utils.geo import bounding_box
from app.models.store import Store
from sqlalchemy import select, and_, func
from geopy.distance import geodesic
from app.models.store_service import StoreService

def search_method2(db, lat, lon, radius_miles, limit: int = 20, store_types: list = None, services: list = None):

    min_lat, min_lon, max_lat, max_lon = bounding_box(lat, lon, radius_miles)
    conditions = [            
            Store.status == "active",
            Store.latitude.between(min_lat, max_lat),
            Store.longitude.between(min_lon, max_lon),
            ]
            
    if store_types:
        conditions.append(Store.store_type.in_(store_types))
    stmt = select(Store).where(
        and_(*conditions)
    )
    if services:
        stmt = (
            stmt.join(StoreService, Store.store_id == StoreService.store_id)
            .where(and_(*conditions))
            .where(StoreService.service_name.in_(services))
            .group_by(Store.store_id)
            .having(func.count(func.distinct(StoreService.service_name)) == len(services)))
    else:
        stmt = stmt.where(and_(*conditions))
    candidates = db.execute(stmt).scalars().all()


    results = []
    for s in candidates:
        d = geodesic((lat, lon), (s.latitude, s.longitude)).miles
        if d <= radius_miles:
            results.append((d, s))
    results.sort(key=lambda x: x[0])
    return results[:limit]

