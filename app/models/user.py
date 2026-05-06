from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)  # e.g., U001
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    role: Mapped[str] = mapped_column(String, nullable=False)  # admin/marketer/viewer

    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active/inactive
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
