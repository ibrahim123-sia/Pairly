"""AI layer tables. All new tables, so existing data is untouched."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class PlatformSetting(Base):
    """Key/value settings owned by the super admin (e.g. the global AI switch)."""

    __tablename__ = "platform_settings"

    key = Column(String(64), primary_key=True)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class StoreAISettings(Base):
    """Per-store AI switches. No row means the defaults (both switches on, global limit)."""

    __tablename__ = "store_ai_settings"

    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)
    # Set by the store manager in Settings.
    ai_enabled = Column(Boolean, nullable=False, default=True)
    # Set by the super admin; a store manager cannot override it.
    admin_ai_enabled = Column(Boolean, nullable=False, default=True)
    # Requests per UTC day; NULL means AI_DAILY_REQUEST_LIMIT.
    daily_limit = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIUsageLog(Base):
    """One row per user-facing AI request (an insights generation or a chat answer)."""

    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    feature = Column(String(32), nullable=False)  # insights | chat
    provider = Column(String(32), nullable=True)
    model = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False)  # ok | fallback | error
    llm_calls = Column(Integer, nullable=False, default=0)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AIInsightCache(Base):
    """Generated dashboard insights, cached per store + dataset + thresholds."""

    __tablename__ = "ai_insight_cache"
    __table_args__ = (UniqueConstraint("store_id", "dataset_id", "params_key", name="uq_ai_insight_cache_key"),)

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    params_key = Column(String(128), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
