from _bootstrap import add_project_root

add_project_root()

from app.db.session import SessionLocal
from app.models.service import Service
from app.models.store_service import StoreService

def run():
    db = SessionLocal()
    try:
        # services
        db.merge(Service(name="pharmacy"))
        db.merge(Service(name="repair"))
        db.merge(Service(name="pickup"))
        db.commit()

        # store_services: 让 S0001 有 pharmacy+repair；S0002 只有 pharmacy
        db.merge(StoreService(store_id="S0001", service_name="pharmacy"))
        db.merge(StoreService(store_id="S0001", service_name="repair"))
        db.merge(StoreService(store_id="S0002", service_name="pharmacy"))
        db.commit()

        print("Seed services OK")
    finally:
        db.close()

if __name__ == "__main__":
    run()
