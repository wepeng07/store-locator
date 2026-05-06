from sqlalchemy import Column, String, ForeignKey
from app.db.base import Base

class StoreService(Base):
    __tablename__ = "store_services"
    store_id = Column(String, ForeignKey("stores.store_id"), primary_key=True)
    service_name = Column(String, ForeignKey("services.name"), primary_key=True)
