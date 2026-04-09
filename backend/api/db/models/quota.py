"""Quota management ORM models for commercial features."""
from sqlalchemy import String, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from backend.api.db.base import Base, BaseModel


class UserQuota(Base, BaseModel):
    """User quota limits for various resources."""
    __tablename__ = 'user_quotas'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        primary_key=True
    )
    article_daily_limit: Mapped[int] = mapped_column(Integer, default=10)
    article_monthly_limit: Mapped[int] = mapped_column(Integer, default=300)
    api_daily_limit: Mapped[int] = mapped_column(Integer, default=1000)
    api_monthly_limit: Mapped[int] = mapped_column(Integer, default=30000)
    storage_limit_mb: Mapped[int] = mapped_column(Integer, default=1000)


class QuotaUsage(Base, BaseModel):
    """Quota consumption tracking records."""
    __tablename__ = 'quota_usage'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    quota_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # article_generation, api_call, storage
    consumed: Mapped[int] = mapped_column(Integer, default=1)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, monthly
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index('ix_quota_usage_user_type_period', 'user_id', 'quota_type', 'period'),
    )
