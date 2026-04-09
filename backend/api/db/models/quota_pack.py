"""Quota pack ORM models for payment system."""
from uuid import UUID
from sqlalchemy import String, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import datetime
from backend.api.db.base import Base


class QuotaPack(Base):
    """Quota pack model for additional quota purchases."""
    __tablename__ = 'quota_packs'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Quota pack information
    pack_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'pack_10', 'pack_50'
    total_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    used_quota: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remaining_quota: Mapped[int] = mapped_column(Integer, nullable=False)  # Denormalized for efficient queries

    # Associated order
    order_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('orders.id', ondelete='SET NULL'),
        nullable=True
    )

    # Validity period
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    order: Mapped[Optional["Order"]] = relationship("Order")

    __table_args__ = (
        Index('ix_quota_pack_user_active', 'user_id', 'expires_at'),
    )
