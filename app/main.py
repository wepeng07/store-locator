from fastapi import Depends, FastAPI
from sqlalchemy import text

from app.db.deps import get_db

app = FastAPI(title="Store Locator Service")

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
