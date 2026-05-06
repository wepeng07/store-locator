from _bootstrap import add_project_root

add_project_root()

from app.db.session import SessionLocal
from app.models.store_service import StoreService

db = SessionLocal()
rows = db.query(StoreService).all()
print([(r.store_id, r.service_name) for r in rows])
db.close()
