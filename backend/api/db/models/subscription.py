"""Subscription ORM models for payment system."""
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import datetime
from backend.api.db.base import Base


class Subscription(Base):
    """User subscription model for tracking paid plans."""
    __tablename__ = 'subscriptions'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True
    )

    # Subscription information
    plan: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'pro', 'ultra'
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # 'monthly', 'quarterly', 'yearly'
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'active', 'cancelled', 'expired'

    # Period timestamps
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Auto-renewal settings
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscription")

    __table_args__ = (
        Index('ix_subscription_user_status', 'user_id', 'status'),
    )
