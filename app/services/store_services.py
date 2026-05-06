from sqlalchemy import select
from app.models.store_service import StoreService

def get_services_for_store_ids(db, store_ids: list[str]) -> dict[str, list[str]]:
    if not store_ids:
        return {}

    rows = db.execute(
        select(StoreService.store_id, StoreService.service_name)
        .where(StoreService.store_id.in_(store_ids))
    ).all()

    mp: dict[str, list[str]] = {sid: [] for sid in store_ids}
    for sid, sname in rows:
        mp.setdefault(sid, []).append(sname)
    for sid in mp:
        mp[sid].sort()
    return mp
