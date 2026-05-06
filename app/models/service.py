from sqlalchemy import Column, String
from app.db.base import Base

class Service(Base):
    __tablename__ = "services"
    name = Column(String, primary_key=True)  # 用 name 做主键，天然去重
