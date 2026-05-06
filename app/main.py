from app.api.routes.admin_ping import router as admin_ping_router
from app.api.routes.admin_stores import router as admin_stores_router
from app.api.routes.auth import router as auth_router
from fastapi import Depends, FastAPI
from sqlalchemy import text

from app.api.routes.stores import router as stores_router
from app.db.deps import get_db
from app.middlewares.rate_limit import RateLimitMiddleware

app = FastAPI(title="Store Locator Service")
app.add_middleware(RateLimitMiddleware, per_minute=10, per_hour=100)

@app.get("/health")
def health_check():
    return {"status": "OK"}

@app.get("/db-health")
def db_health(db=Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "OK"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


app.include_router(stores_router)
app.include_router(auth_router)
app.include_router(admin_ping_router)
app.include_router(admin_stores_router)
