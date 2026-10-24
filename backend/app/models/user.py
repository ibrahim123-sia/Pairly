from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole:
    SUPER_ADMIN = "super_admin"
    STORE_MANAGER = "store_manager"
    ALL = (SUPER_ADMIN, STORE_MANAGER)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default=UserRole.STORE_MANAGER)
    full_name = Column(String(255), nullable=False, default="")
    is_email_verified = Column(Boolean, nullable=False, default=True)
    email_verification_token = Column(String(255), nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_count = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    store = relationship(
        "Store",
        foreign_keys=[store_id],
        back_populates="users",
    )

    def to_dict(self, include_store=False):
        data = {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "must_change_password": self.must_change_password,
            "store_id": self.store_id,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_store and self.store:
            data["store"] = self.store.to_dict()
        return data

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_store_manager(self):
        return self.role == UserRole.STORE_MANAGER
