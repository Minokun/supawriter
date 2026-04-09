"""Alert and notification ORM models for Sprint 6."""
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from typing import Optional
from uuid import UUID as UUID_TYPE, uuid4
from datetime import datetime, timezone
from backend.api.db.base import Base


class AlertKeyword(Base):
    """User alert keyword model for hotspot matching."""
    __tablename__ = 'alert_keywords'

    id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="alert_keywords")
    alert_records: Mapped[list["AlertRecord"]] = relationship(
        "AlertRecord",
        back_populates="keyword",
        cascade="all, delete-orphan"
    )


class AlertRecord(Base):
    """Alert record model for matched hotspots."""
    __tablename__ = 'alert_records'

    id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    keyword_id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('alert_keywords.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    hotspot_title: Mapped[str] = mapped_column(String(500), nullable=False)
    hotspot_source: Mapped[str] = mapped_column(String(50), nullable=False)  # baidu, weibo, etc.
    hotspot_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    hotspot_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Original hotspot ID for deduplication
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="alert_records")
    keyword: Mapped["AlertKeyword"] = relationship("AlertKeyword", back_populates="alert_records")


class UserStats(Base):
    """User statistics cache model for dashboard."""
    __tablename__ = 'user_stats'

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        primary_key=True
    )

    # Basic stats (Free tier)
    total_articles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_words: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_articles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Pro tier stats
    avg_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_history: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # [{"date": "2026-02", "score": 72}]
    platform_stats: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {"wechat": 10, "zhihu": 5}

    # Ultra tier stats
    hotspot_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    keyword_hit_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_usage: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {"deepseek": 20, "openai": 5}

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="user_stats")
