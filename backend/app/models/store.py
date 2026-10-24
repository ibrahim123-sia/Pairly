from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    theme_mode = Column(String(16), nullable=False, default="light")
    brand_primary_color = Column(String(16), nullable=True)
    brand_logo_path = Column(String(512), nullable=True)
    active_dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="SET NULL", use_alter=True, name="fk_store_active_dataset"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    disabled_at = Column(DateTime, nullable=True)
    disabled_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship(
        "User",
        foreign_keys="User.store_id",
        back_populates="store",
        cascade="save-update, merge",
    )
    datasets = relationship(
        "Dataset",
        foreign_keys="Dataset.store_id",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    active_dataset = relationship(
        "Dataset",
        foreign_keys=[active_dataset_id],
        post_update=True,
    )

    def to_dict(self, include_counts=False):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "contact_email": self.contact_email,
            "is_active": self.is_active,
            "theme_mode": self.theme_mode,
            "brand_primary_color": self.brand_primary_color,
            "active_dataset_id": self.active_dataset_id,
            "disabled_at": self.disabled_at.isoformat() if self.disabled_at else None,
            "disabled_reason": self.disabled_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_counts:
            manager = next((u for u in self.users if u.role == "store_manager"), None)
            data["manager_email"] = manager.email if manager else None
            data["manager_name"] = manager.full_name if manager else None
            data["dataset_count"] = len(self.datasets)
            last_upload = max((d.uploaded_at for d in self.datasets), default=None)
            data["last_upload_at"] = last_upload.isoformat() if last_upload else None
        return data
