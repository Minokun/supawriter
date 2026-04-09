"""Quota service with commercial features business logic."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from backend.api.repositories.quota import QuotaRepository


class QuotaService:
    """
    Service layer for quota management.

    Handles business logic for quota checking, consumption tracking,
    limit management, and usage reporting for commercial features.
    """

    def __init__(self, session: AsyncSession, quota_repository: QuotaRepository):
        """
        Initialize QuotaService.

        Args:
            session: Database session
            quota_repository: Quota repository instance
        """
        self.session = session
        self.quota_repo = quota_repository

    async def check_and_consume_quota(
        self,
        user_id: int,
        quota_type: str,
        amount: int,
        period: str
    ) -> Tuple[bool, int]:
        """
        Check quota availability and consume if available.

        Args:
            user_id: User ID
            quota_type: Type of quota (article_generation, api_call, storage)
            amount: Amount to consume
            period: Period (daily, monthly)

        Returns:
            Tuple of (success: bool, remaining: int)
        """
        return await self.quota_repo.check_and_consume(user_id, quota_type, amount, period)

    async def check_quota_available(
        self,
        user_id: int,
        quota_type: str,
        amount: int,
        period: str
    ) -> bool:
        """
        Check if quota is available without consuming.

        Args:
            user_id: User ID
            quota_type: Type of quota
            amount: Amount to check
            period: Period (daily, monthly)

        Returns:
            True if quota is available, False otherwise
        """
        return await self.quota_repo.check_quota_available(user_id, quota_type, period, amount)

    async def get_user_quota_info(self, user_id: int) -> Optional[Dict]:
        """
        Get comprehensive quota information for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with quota limits and usage, or None if not found
        """
        quota = await self.quota_repo.get_user_quota(user_id)
        if not quota:
            return None

        usage_summary = await self.quota_repo.get_quota_summary(user_id)

        return {
            "user_id": user_id,
            "article_daily_limit": quota.article_daily_limit,
            "article_monthly_limit": quota.article_monthly_limit,
            "api_daily_limit": quota.api_daily_limit,
            "api_monthly_limit": quota.api_monthly_limit,
            "storage_limit_mb": quota.storage_limit_mb,
            "usage": usage_summary,
        }

    async def get_usage_summary(
        self,
        user_id: int,
        days: int = 30
    ) -> Optional[Dict]:
        """
        Get usage summary for a user over a period.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Dictionary with usage by quota type and period
        """
        quota = await self.quota_repo.get_user_quota(user_id)
        if not quota:
            return None

        return await self.quota_repo.get_quota_summary(user_id)

    async def reset_period_usage(
        self,
        user_id: int,
        period: str,
        quota_type: Optional[str] = None
    ) -> int:
        """
        Reset usage records for a specific period.

        Args:
            user_id: User ID
            period: Period to reset (daily, monthly)
            quota_type: Optional quota type to reset

        Returns:
            Number of records deleted
        """
        return await self.quota_repo.reset_period_usage(user_id, period, quota_type)

    async def initialize_user_quotas(
        self,
        user_id: int,
        article_daily_limit: int = 10,
        article_monthly_limit: int = 300,
        api_daily_limit: int = 1000,
        api_monthly_limit: int = 30000,
        storage_limit_mb: int = 1000
    ):
        """
        Initialize default quotas for a new user.

        Args:
            user_id: User ID
            article_daily_limit: Daily article generation limit
            article_monthly_limit: Monthly article generation limit
            api_daily_limit: Daily API call limit
            api_monthly_limit: Monthly API call limit
            storage_limit_mb: Storage limit in MB

        Returns:
            Created UserQuota instance
        """
        return await self.quota_repo.create_user_quota(
            user_id=user_id,
            article_daily_limit=article_daily_limit,
            article_monthly_limit=article_monthly_limit,
            api_daily_limit=api_daily_limit,
            api_monthly_limit=api_monthly_limit,
            storage_limit_mb=storage_limit_mb
        )

    async def update_quota_limits(
        self,
        user_id: int,
        article_daily_limit: Optional[int] = None,
        article_monthly_limit: Optional[int] = None,
        api_daily_limit: Optional[int] = None,
        api_monthly_limit: Optional[int] = None,
        storage_limit_mb: Optional[int] = None
    ):
        """
        Update quota limits for a user.

        Args:
            user_id: User ID
            article_daily_limit: New daily article limit
            article_monthly_limit: New monthly article limit
            api_daily_limit: New daily API limit
            api_monthly_limit: New monthly API limit
            storage_limit_mb: New storage limit

        Returns:
            Updated UserQuota instance or None if not found
        """
        return await self.quota_repo.update_limits(
            user_id=user_id,
            article_daily_limit=article_daily_limit,
            article_monthly_limit=article_monthly_limit,
            api_daily_limit=api_daily_limit,
            api_monthly_limit=api_monthly_limit,
            storage_limit_mb=storage_limit_mb
        )

    async def get_over_limit_users(
        self,
        quota_type: str,
        period: str
    ) -> List[int]:
        """
        Get list of user IDs who are over their quota limit.

        Args:
            quota_type: Type of quota
            period: Period (daily, monthly)

        Returns:
            List of user IDs
        """
        # Get all users with quotas and check each one
        # For a production system, this should be optimized with a single query
        over_limit_users = []

        # Get all quota usage records for this quota type and period
        usage_records = await self.quota_repo.usage_repo.list(
            filters={"quota_type": quota_type, "period": period}
        )

        # Group usage by user_id
        user_usage = {}
        for record in usage_records:
            user_id = record.user_id
            if user_id not in user_usage:
                user_usage[user_id] = 0
            user_usage[user_id] += record.consumed

        # Check each user against their quota limit
        for user_id, total_usage in user_usage.items():
            quota = await self.quota_repo.get_user_quota(user_id)
            if not quota:
                continue

            # Get the limit for this quota type and period
            limit_field = self.quota_repo._get_limit_field(quota_type, period)
            limit = getattr(quota, limit_field, 0)

            if total_usage > limit:
                over_limit_users.append(user_id)

        return over_limit_users

    async def bulk_record_usage(
        self,
        user_id: int,
        usages: List[Dict]
    ) -> int:
        """
        Bulk record quota usage.

        Args:
            user_id: User ID
            usages: List of dictionaries with quota_type, amount, period

        Returns:
            Number of usage records created
        """
        count = 0
        for usage in usages:
            await self.quota_repo.record_usage(
                user_id=user_id,
                quota_type=usage["quota_type"],
                consumed=usage["amount"],
                period=usage["period"]
            )
            count += 1

        return count

    async def get_quota_remaining(
        self,
        user_id: int,
        quota_type: str,
        period: str
    ) -> int:
        """
        Get remaining quota for a user.

        Args:
            user_id: User ID
            quota_type: Type of quota
            period: Period (daily, monthly)

        Returns:
            Remaining quota count
        """
        return await self.quota_repo.get_remaining_quota(user_id, quota_type, period)

    async def get_quota_usage_history(
        self,
        user_id: int,
        limit: int = 100
    ):
        """
        Get quota usage history for a user.

        Args:
            user_id: User ID
            limit: Maximum records to return

        Returns:
            List of QuotaUsage instances
        """
        return await self.quota_repo.get_usage_history(user_id, limit)

    async def upgrade_user_quotas(
        self,
        user_id: int,
        tier: str
    ) -> Optional[Dict]:
        """
        Upgrade user to a different quota tier.

        Args:
            user_id: User ID
            tier: Tier name (free, pro, enterprise)

        Returns:
            Dictionary with new quota limits or None if tier not found
        """
        # Define tier configurations
        tiers = {
            "free": {
                "article_daily_limit": 10,
                "article_monthly_limit": 300,
                "api_daily_limit": 1000,
                "api_monthly_limit": 30000,
                "storage_limit_mb": 1000,
            },
            "pro": {
                "article_daily_limit": 50,
                "article_monthly_limit": 1500,
                "api_daily_limit": 5000,
                "api_monthly_limit": 150000,
                "storage_limit_mb": 10000,
            },
            "enterprise": {
                "article_daily_limit": 500,
                "article_monthly_limit": 15000,
                "api_daily_limit": 50000,
                "api_monthly_limit": 1500000,
                "storage_limit_mb": 100000,
            },
        }

        tier_config = tiers.get(tier)
        if not tier_config:
            return None

        # Update user quotas
        quota = await self.update_quota_limits(user_id, **tier_config)

        return {
            "tier": tier,
            "limits": tier_config,
        }

    async def check_storage_quota(
        self,
        user_id: int,
        additional_mb: int
    ) -> bool:
        """
        Check if user has enough storage quota.

        Args:
            user_id: User ID
            additional_mb: Additional storage in MB

        Returns:
            True if storage is available, False otherwise
        """
        # Get total storage used
        usage_summary = await self.quota_repo.get_quota_summary(user_id)

        storage_used = 0
        if "storage" in usage_summary:
            for period_data in usage_summary["storage"].values():
                storage_used += period_data

        # Get user's storage limit
        quota = await self.quota_repo.get_user_quota(user_id)
        if not quota:
            return False

        return storage_used + additional_mb <= quota.storage_limit_mb

    async def get_quota_report(
        self,
        user_id: int
    ) -> Dict:
        """
        Generate a comprehensive quota report for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with quota status, usage, and recommendations
        """
        quota = await self.quota_repo.get_user_quota(user_id)
        if not quota:
            return {"error": "User quota not found"}

        usage = await self.quota_repo.get_quota_summary(user_id)

        report = {
            "user_id": user_id,
            "limits": {
                "article_daily": quota.article_daily_limit,
                "article_monthly": quota.article_monthly_limit,
                "api_daily": quota.api_daily_limit,
                "api_monthly": quota.api_monthly_limit,
                "storage_mb": quota.storage_limit_mb,
            },
            "usage": {},
            "remaining": {},
            "utilization": {},
        }

        # Calculate usage, remaining, and utilization for each quota type
        for quota_type, period_prefix in [
            ("article_generation", "article"),
            ("api_call", "api"),
            ("storage", "storage"),
        ]:
            for period in ["daily", "monthly"]:
                limit_field = f"{period_prefix}_{period}_limit"
                limit = getattr(quota, limit_field, 0)

                used = 0
                if quota_type in usage:
                    used = usage[quota_type].get(period, 0)

                remaining = max(0, limit - used)
                utilization = (used / limit * 100) if limit > 0 else 0

                report["usage"].setdefault(quota_type, {})[period] = used
                report["remaining"].setdefault(quota_type, {})[period] = remaining
                report["utilization"].setdefault(quota_type, {})[period] = round(utilization, 2)

        return report
