"""Subscription service for managing user subscriptions and quota."""
from uuid import uuid4, UUID
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text

from backend.api.repositories.payment import (
    SubscriptionRepository,
    OrderRepository,
    QuotaPackRepository
)
from backend.api.services.pricing_service import PricingService
from backend.api.db.models import Subscription, Order, QuotaPack


class SubscriptionService:
    """
    Service for managing subscriptions and quota.

    Handles subscription upgrades, cancellations, quota checking,
    and quota consumption with priority logic.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize SubscriptionService.

        Args:
            session: Database session
        """
        self.session = session
        self.subscription_repo = SubscriptionRepository(session)
        self.order_repo = OrderRepository(session)
        self.quota_pack_repo = QuotaPackRepository(session)

    async def get_user_subscription(
        self,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get current user subscription information.

        Uses users.membership_tier as the source of truth for the user's plan,
        supplemented by subscription table for billing details.

        Args:
            user_id: User ID

        Returns:
            Dictionary with subscription details or None
        """
        # Read membership_tier AND is_superuser to detect superadmin
        tier_result = await self.session.execute(
            text("SELECT membership_tier, is_superuser, email FROM users WHERE id = :uid"),
            {"uid": user_id}
        )
        tier_row = tier_result.fetchone()
        membership_tier = tier_row[0] if tier_row else 'free'
        is_superuser = tier_row[1] if tier_row else False
        user_email = tier_row[2] if tier_row else ''

        subscription = await self.subscription_repo.get_active_subscription(user_id)

        # Check if user is a true superadmin (email whitelist + is_superuser flag)
        from backend.api.services.tier_service import get_super_admin_emails
        super_admin_emails = get_super_admin_emails()
        is_superadmin = is_superuser and user_email in super_admin_emails

        # Determine feature tier: superadmin always wins
        if is_superadmin:
            feature_tier = 'superuser'
        else:
            feature_tier = membership_tier

        billing_plan = subscription.plan if subscription else None
        has_active_subscription = subscription is not None
        billing_status = subscription.status if subscription else "inactive"

        # Superuser: unlimited quota, skip article counting
        if feature_tier == 'superuser':
            return {
                "feature_tier": "superuser",
                "billing_plan": billing_plan,
                "has_active_subscription": has_active_subscription,
                "current_plan": "superuser",
                "current_period": subscription.period if subscription else None,
                "status": billing_status,
                "current_period_start": None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
                "auto_renew": subscription.auto_renew if subscription else False,
                "quota": {
                    "monthly_limit": 999999,
                    "monthly_used": 0,
                    "pack_remaining": 0
                }
            }

        # Get monthly usage from articles
        from backend.api.db.models import Article
        start_of_month = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        stmt = select(func.count()).select_from(Article).where(
            and_(
                Article.user_id == user_id,
                Article.created_at >= start_of_month
            )
        )
        result = await self.session.execute(stmt)
        monthly_used = result.scalar() or 0

        # Get pack remaining quota
        pack_quota = await self.quota_pack_repo.get_total_remaining_quota(user_id)

        plan_quota = PricingService.get_plan_quota(feature_tier)

        if subscription:
            return {
                "feature_tier": feature_tier,
                "billing_plan": billing_plan,
                "has_active_subscription": has_active_subscription,
                "current_plan": feature_tier,
                "current_period": subscription.period,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "auto_renew": subscription.auto_renew,
                "quota": {
                    "monthly_limit": plan_quota,
                    "monthly_used": monthly_used,
                    "pack_remaining": pack_quota
                }
            }

        # No active subscription — return based on membership_tier
        return {
            "feature_tier": feature_tier,
            "billing_plan": None,
            "has_active_subscription": False,
            "current_plan": feature_tier,
            "current_period": None,
            "status": "inactive",
            "current_period_start": None,
            "current_period_end": None,
            "auto_renew": False,
            "quota": {
                "monthly_limit": plan_quota,
                "monthly_used": monthly_used,
                "pack_remaining": pack_quota
            }
        }

    async def _get_effective_plan(self, user_id: int) -> str:
        """Get the effective plan from membership_tier + superadmin check."""
        tier_result = await self.session.execute(
            text("SELECT membership_tier, is_superuser, email FROM users WHERE id = :uid"),
            {"uid": user_id}
        )
        tier_row = tier_result.fetchone()
        if not tier_row:
            return 'free'

        membership_tier = tier_row[0]
        is_superuser = tier_row[1]
        user_email = tier_row[2]

        # Check superadmin (email whitelist + is_superuser flag)
        from backend.api.services.tier_service import get_super_admin_emails
        super_admin_emails = get_super_admin_emails()
        if is_superuser and user_email in super_admin_emails:
            return 'superuser'

        return membership_tier

    async def check_quota(
        self,
        user_id: int,
        amount: int = 1
    ) -> Dict[str, Any]:
        """
        Check if user has enough quota.

        Priority: Monthly plan quota > Quota packs

        Args:
            user_id: User ID
            amount: Amount of quota to check

        Returns:
            Dictionary with quota status
        """
        effective_plan = await self._get_effective_plan(user_id)

        # Superuser: unlimited quota, always allowed
        if effective_plan == 'superuser':
            return {
                "allowed": True,
                "monthly_limit": 999999,
                "monthly_used": 0,
                "monthly_remaining": 999999,
                "pack_remaining": 0,
                "total_remaining": 999999,
                "source": "monthly"
            }

        # Get monthly usage from articles
        from backend.api.db.models import Article
        start_of_month = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        stmt = select(func.count()).select_from(Article).where(
            and_(
                Article.user_id == user_id,
                Article.created_at >= start_of_month
            )
        )
        result = await self.session.execute(stmt)
        monthly_used = result.scalar() or 0

        plan_quota = PricingService.get_plan_quota(effective_plan)
        monthly_remaining = max(0, plan_quota - monthly_used)

        # Get pack quota
        pack_quota = await self.quota_pack_repo.get_total_remaining_quota(user_id)
        total_remaining = monthly_remaining + pack_quota

        # Get pack quota
        pack_quota = await self.quota_pack_repo.get_total_remaining_quota(user_id)
        total_remaining = monthly_remaining + pack_quota

        # Determine if quota is available
        if monthly_used + amount <= plan_quota:
            return {
                "allowed": True,
                "monthly_limit": plan_quota,
                "monthly_used": monthly_used,
                "monthly_remaining": monthly_remaining,
                "pack_remaining": pack_quota,
                "total_remaining": total_remaining,
                "source": "monthly"
            }
        elif total_remaining >= amount:
            return {
                "allowed": True,
                "monthly_limit": plan_quota,
                "monthly_used": monthly_used,
                "monthly_remaining": monthly_remaining,
                "pack_remaining": pack_quota,
                "total_remaining": total_remaining,
                "source": "pack"
            }
        else:
            return {
                "allowed": False,
                "monthly_limit": plan_quota,
                "monthly_used": monthly_used,
                "monthly_remaining": monthly_remaining,
                "pack_remaining": pack_quota,
                "total_remaining": total_remaining,
                "source": None
            }

    async def use_quota(
        self,
        user_id: int,
        amount: int = 1
    ) -> Dict[str, Any]:
        """
        Consume quota from user's account.

        Priority: Monthly plan quota > Quota packs (FIFO by expiry)

        Args:
            user_id: User ID
            amount: Amount of quota to consume

        Returns:
            Dictionary with consumption result
        """
        quota_status = await self.check_quota(user_id, amount)

        if not quota_status["allowed"]:
            return {
                "success": False,
                "message": "Insufficient quota",
                "quota_status": quota_status
            }

        # If monthly quota is available, no action needed (tracked by article count)
        # Only consume from packs if monthly quota is exhausted
        if quota_status["source"] == "pack":
            consumed = await self.quota_pack_repo.consume_quota(user_id, amount)
            if not consumed:
                return {
                    "success": False,
                    "message": "Failed to consume quota from packs",
                    "quota_status": quota_status
                }

        return {
            "success": True,
            "message": "Quota consumed successfully",
            "quota_status": quota_status
        }

    async def upgrade_subscription(
        self,
        user_id: int,
        plan: str,
        period: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Upgrade subscription (simulated payment flow).
        Downgrade is not allowed to avoid refund complexity.

        Args:
            user_id: User ID
            plan: Target plan ('pro', 'ultra')
            period: Billing period ('monthly', 'quarterly', 'yearly')

        Returns:
            Dictionary with order information
        """
        # Validate plan
        plan_config = PricingService.get_plan_by_id(plan)
        if not plan_config:
            return {
                "success": False,
                "message": "Invalid plan"
            }

        # Prevent downgrade — check both subscription and membership_tier
        TIER_ORDER = {"free": 0, "pro": 1, "ultra": 2, "superuser": 3}
        current_sub = await self.subscription_repo.get_active_subscription(user_id)
        # Also check membership_tier for the real current tier
        tier_result = await self.session.execute(
            text("SELECT membership_tier FROM users WHERE id = :uid"),
            {"uid": user_id}
        )
        tier_row = tier_result.fetchone()
        membership_tier = tier_row[0] if tier_row else 'free'

        sub_plan = current_sub.plan if current_sub else "free"
        # Use the highest tier between subscription and membership_tier
        current_plan = sub_plan if TIER_ORDER.get(sub_plan, 0) >= TIER_ORDER.get(membership_tier, 0) else membership_tier

        if TIER_ORDER.get(plan, 0) <= TIER_ORDER.get(current_plan, 0):
            return {
                "success": False,
                "message": "暂不支持降级，如需帮助请联系客服"
            }

        # Calculate price
        amount_cents = PricingService.calculate_price(plan, period)

        # Create pending order
        order_id = uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)  # Order expires in 24 hours

        order = await self.order_repo.create(
            id=order_id,
            user_id=user_id,
            order_type="subscription",
            plan=plan,
            period=period,
            amount_cents=amount_cents,
            status="pending",
            expires_at=expires_at,
            created_at=now
        )

        # Update user's subscription immediately for simulation
        # In production, this would happen after payment confirmation
        await self._apply_subscription(
            user_id=user_id,
            plan=plan,
            period=period,
            order_id=order_id
        )

        return {
            "success": True,
            "order_id": str(order.id),
            "status": "paid",  # Simulated
            "amount": amount_cents,
            "message": "订阅已更新（模拟支付）"
        }

    async def _apply_subscription(
        self,
        user_id: int,
        plan: str,
        period: str,
        order_id: UUID
    ) -> Subscription:
        """
        Apply subscription to user's account.

        Args:
            user_id: User ID
            plan: Plan identifier
            period: Billing period
            order_id: Associated order ID

        Returns:
            Created or updated Subscription instance
        """
        now = datetime.now(timezone.utc)

        # Calculate period end date
        period_days = {
            "monthly": 30,
            "quarterly": 90,
            "yearly": 365
        }
        days = period_days.get(period, 30)
        period_end = now + timedelta(days=days)

        # Check if subscription exists
        existing = await self.subscription_repo.get_by_user_id(user_id)

        if existing:
            # Update existing subscription
            existing.plan = plan
            existing.period = period
            existing.status = "active"
            existing.current_period_start = now
            existing.current_period_end = period_end
            existing.auto_renew = False
            existing.cancelled_at = None
            existing.updated_at = now

            subscription = existing
        else:
            # Create new subscription
            subscription = await self.subscription_repo.create(
                user_id=user_id,
                plan=plan,
                period=period,
                status="active",
                current_period_start=now,
                current_period_end=period_end,
                auto_renew=False,
                created_at=now,
                updated_at=now
            )

        # Sync users.membership_tier so TierService sees the correct tier
        await self.session.execute(
            text("UPDATE users SET membership_tier = :tier, updated_at = NOW() WHERE id = :uid"),
            {"tier": plan, "uid": user_id}
        )

        return subscription

    async def cancel_subscription(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Cancel user's subscription.

        Args:
            user_id: User ID

        Returns:
            Dictionary with cancellation result
        """
        subscription = await self.subscription_repo.get_active_subscription(user_id)

        if not subscription:
            return {
                "success": False,
                "message": "No active subscription found"
            }

        # Mark as cancelled (benefits remain until period end)
        now = datetime.now(timezone.utc)
        subscription.status = "cancelled"
        subscription.cancelled_at = now
        subscription.auto_renew = False
        subscription.updated_at = now

        # If period has already ended, revert membership_tier to free immediately
        if subscription.current_period_end and subscription.current_period_end <= now:
            await self.session.execute(
                text("UPDATE users SET membership_tier = 'free', updated_at = NOW() WHERE id = :uid"),
                {"uid": user_id}
            )

        return {
            "success": True,
            "message": "订阅已取消，当前周期内权益保留",
            "current_period_end": subscription.current_period_end.isoformat()
        }

    async def purchase_quota_pack(
        self,
        user_id: int,
        pack_type: str
    ) -> Dict[str, Any]:
        """
        Purchase a quota pack (simulated payment flow).

        Args:
            user_id: User ID
            pack_type: Pack identifier ('pack_10', 'pack_50')

        Returns:
            Dictionary with order and pack information
        """
        # Validate pack
        pack_config = PricingService.get_quota_pack_by_id(pack_type)
        if not pack_config:
            return {
                "success": False,
                "message": "Invalid quota pack"
            }

        # Create pending order
        order_id = uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        order = await self.order_repo.create(
            id=order_id,
            user_id=user_id,
            order_type="quota_pack",
            pack_type=pack_type,
            quota_amount=pack_config["quota"],
            amount_cents=pack_config["price"],
            status="paid",  # Simulated
            created_at=now
        )

        # Create quota pack
        pack_expires = now + timedelta(days=pack_config["validity_days"])

        quota_pack = await self.quota_pack_repo.create(
            user_id=user_id,
            pack_type=pack_type,
            total_quota=pack_config["quota"],
            used_quota=0,
            remaining_quota=pack_config["quota"],
            order_id=order_id,
            purchased_at=now,
            expires_at=pack_expires
        )

        return {
            "success": True,
            "order_id": str(order_id),
            "pack_id": quota_pack.id,
            "quota": pack_config["quota"],
            "expires_at": pack_expires.isoformat(),
            "message": "额度包已购买（模拟支付）"
        }

    async def get_quota_details(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get detailed quota information for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with quota breakdown
        """
        effective_plan = await self._get_effective_plan(user_id)

        # Superuser: unlimited quota
        if effective_plan == 'superuser':
            return {
                "plan_quota": 999999,
                "plan_used": 0,
                "plan_remaining": 999999,
                "pack_quota": 0,
                "pack_remaining": 0,
                "total_remaining": 999999,
                "packs": []
            }

        # Get monthly usage
        from backend.api.db.models import Article
        start_of_month = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        stmt = select(func.count()).select_from(Article).where(
            and_(
                Article.user_id == user_id,
                Article.created_at >= start_of_month
            )
        )
        result = await self.session.execute(stmt)
        monthly_used = result.scalar() or 0

        # Get pack quota
        packs = await self.quota_pack_repo.get_user_quota_packs(user_id, active_only=True)
        pack_quota = sum(p.remaining_quota for p in packs)

        plan_quota = PricingService.get_plan_quota(effective_plan)
        monthly_remaining = max(0, plan_quota - monthly_used)

        return {
            "plan_quota": plan_quota,
            "plan_used": monthly_used,
            "plan_remaining": monthly_remaining,
            "pack_quota": pack_quota,
            "pack_remaining": pack_quota,
            "total_remaining": monthly_remaining + pack_quota,
            "packs": [
                {
                    "id": p.id,
                    "pack_type": p.pack_type,
                    "remaining": p.remaining_quota,
                    "expires_at": p.expires_at.isoformat()
                }
                for p in packs
            ]
        }
