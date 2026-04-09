"""Repository layer for payment system models."""
from uuid import UUID
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from backend.api.repositories.base import BaseRepository
from backend.api.db.models import Subscription, Order, QuotaPack


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for Subscription model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Subscription)

    async def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """Get subscription by user ID."""
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get active subscription for a user."""
        now = datetime.now(timezone.utc)
        stmt = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == 'active',
                Subscription.current_period_end > now
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_expiring_subscriptions(
        self,
        days_ahead: int = 7
    ) -> List[Subscription]:
        """Get subscriptions expiring within N days."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        now = datetime.now(timezone.utc)

        stmt = select(Subscription).where(
            and_(
                Subscription.status == 'active',
                Subscription.current_period_end <= cutoff,
                Subscription.current_period_end > now,
                Subscription.auto_renew == True
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class OrderRepository(BaseRepository[Order]):
    """Repository for Order model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Order)

    async def get_by_id(self, id: UUID) -> Optional[Order]:
        """Get order by UUID."""
        stmt = select(Order).where(Order.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_orders(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """Get orders for a user with optional status filter."""
        stmt = select(Order).where(Order.user_id == user_id)

        if status:
            stmt = stmt.where(Order.status == status)

        stmt = stmt.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_orders(self, expires_before: datetime) -> List[Order]:
        """Get pending orders that have expired."""
        stmt = select(Order).where(
            and_(
                Order.status == 'pending',
                Order.expires_at <= expires_before
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class QuotaPackRepository(BaseRepository[QuotaPack]):
    """Repository for QuotaPack model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, QuotaPack)

    async def get_user_quota_packs(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[QuotaPack]:
        """Get quota packs for a user."""
        now = datetime.now(timezone.utc)
        stmt = select(QuotaPack).where(QuotaPack.user_id == user_id)

        if active_only:
            stmt = stmt.where(
                and_(
                    QuotaPack.remaining_quota > 0,
                    QuotaPack.expires_at > now
                )
            )

        stmt = stmt.order_by(QuotaPack.expires_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_remaining_quota(self, user_id: int) -> int:
        """Get total remaining quota from all active packs."""
        now = datetime.now(timezone.utc)
        stmt = select(func.sum(QuotaPack.remaining_quota)).select_from(QuotaPack).where(
            and_(
                QuotaPack.user_id == user_id,
                QuotaPack.remaining_quota > 0,
                QuotaPack.expires_at > now
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def consume_quota(
        self,
        user_id: int,
        amount: int
    ) -> bool:
        """Consume quota from user's packs (FIFO order by expiry)."""
        from sqlalchemy import func, update
        now = datetime.now(timezone.utc)

        # Get packs sorted by expiry date
        packs = await self.get_user_quota_packs(user_id, active_only=True)

        remaining_to_consume = amount
        for pack in packs:
            if remaining_to_consume <= 0:
                break

            can_consume = min(pack.remaining_quota, remaining_to_consume)
            new_remaining = pack.remaining_quota - can_consume
            new_used = pack.used_quota + can_consume

            stmt = (
                update(QuotaPack)
                .where(QuotaPack.id == pack.id)
                .values(
                    remaining_quota=new_remaining,
                    used_quota=new_used
                )
            )
            await self.session.execute(stmt)

            remaining_to_consume -= can_consume

        return remaining_to_consume == 0
