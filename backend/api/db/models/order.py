"""Order ORM models for payment system."""
from uuid import uuid4, UUID
from sqlalchemy import String, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from datetime import datetime
from backend.api.db.base import Base


class Order(Base):
    """Order model for tracking subscription and quota pack purchases."""
    __tablename__ = 'orders'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Order type
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'subscription', 'quota_pack'

    # Subscription related fields
    plan: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'pro', 'ultra'
    period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'monthly', 'quarterly', 'yearly'

    # Quota pack related fields
    pack_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'pack_10', 'pack_50'
    quota_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Amount in cents
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'pending', 'paid', 'cancelled'

    # Payment information (deferred)
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_order_user_status', 'user_id', 'status'),
        Index('ix_order_type_status', 'order_type', 'status'),
    )
