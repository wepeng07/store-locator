from sqlalchemy import Column, String, Float
from app.db.base import Base

class Store(Base):
    __tablename__ = "stores"

    store_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    store_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    address_street = Column(String, nullable=False)
    address_city = Column(String, nullable=False)
    address_state = Column(String(2), nullable=False)
    address_postal_code = Column(String(5), nullable=False)
    address_country = Column(String(3), nullable=False)

    phone = Column(String, nullable=True)
    hours = Column(String, nullable=True)  # e.g. "Mon-Fri 9am-9pm; Sat-Sun 10am-6pm"
