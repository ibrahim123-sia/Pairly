import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class DatasetStatus:
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


def _uuid():
    return str(uuid.uuid4())


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=_uuid)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(512), nullable=False)
    parquet_path = Column(String(1024), nullable=True)
    row_count = Column(Integer, nullable=True)
    column_mapping = Column(JSON, nullable=True)
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default=DatasetStatus.UPLOADED, index=True)
    validation_errors = Column(JSON, nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)

    store = relationship(
        "Store",
        foreign_keys=[store_id],
        back_populates="datasets",
    )

    def to_dict(self, is_active=False):
        return {
            "id": self.id,
            "store_id": self.store_id,
            "original_filename": self.original_filename,
            "row_count": self.row_count,
            "file_size_bytes": self.file_size_bytes,
            "status": self.status,
            "validation_errors": self.validation_errors,
            "date_range_start": self.date_range_start.isoformat() if self.date_range_start else None,
            "date_range_end": self.date_range_end.isoformat() if self.date_range_end else None,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "notes": self.notes,
            "is_active": is_active,
        }
