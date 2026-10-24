from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, unique=True)
    is_enabled = Column(Boolean, nullable=False, default=False)
    cron_expression = Column(String(64), nullable=False, default="0 2 * * *")
    email_summary_to = Column(String(255), nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(32), nullable=True)
    last_run_error = Column(Text, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "store_id": self.store_id,
            "is_enabled": self.is_enabled,
            "cron_expression": self.cron_expression,
            "email_summary_to": self.email_summary_to,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "last_run_error": self.last_run_error,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
        }
