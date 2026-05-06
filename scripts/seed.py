import json

from _bootstrap import add_project_root

add_project_root()

from app.db.session import SessionLocal
from app.models.service import Service  # 可选
from app.models.store import Store
from app.models.store_service import StoreService

def run():
    db = SessionLocal()
    try:
        # ✅ 先删子表
        db.query(StoreService).delete()
        db.query(Store).delete()
        db.query(Service).delete()  # 可选：如果你想每次都重建 services

        hours = json.dumps({
            "timezone": "America/New_York",
            "weekly": {
                "mon": [["09:00","17:00"]],
                "tue": [["09:00","17:00"]],
                "wed": [["09:00","17:00"]],
                "thu": [["09:00","17:00"]],
                "fri": [["09:00","17:00"]],
                "sat": [],
                "sun": []
            }
        })

        db.add_all([
            Store(
                store_id="S0001", name="Boston Downtown",
                store_type="regular", status="active",
                latitude=42.355, longitude=-71.060,
                address_street="1 Main St", address_city="Boston",
                address_state="MA", address_postal_code="02110", address_country="USA",
                hours=hours,
            ),
            Store(
                store_id="S0002", name="Cambridge Center",
                store_type="express", status="active",
                latitude=42.365, longitude=-71.104,
                address_street="2 Main St", address_city="Cambridge",
                address_state="MA", address_postal_code="02139", address_country="USA",
                hours=hours,
            ),
            Store(
                store_id="S0003", name="Far Away Store",
                store_type="outlet", status="active",
                latitude=40.7128, longitude=-74.0060,
                address_street="3 Main St", address_city="New York",
                address_state="NY", address_postal_code="10007", address_country="USA",
                hours=hours,
            ),
        ])
        db.commit()
        print("Seed OK: inserted 3 stores")
    finally:
        db.close()

if __name__ == "__main__":
    run()
