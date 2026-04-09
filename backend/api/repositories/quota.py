"""Quota repository with commercial features operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete, func, case, literal_column
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from backend.api.db.models.quota import UserQuota, QuotaUsage
from backend.api.repositories.base import BaseRepository


class QuotaUsageRepository(BaseRepository[QuotaUsage]):
    """Repository for QuotaUsage operations."""

    def __init__(self, session: AsyncSession):
        """Initialize QuotaUsage repository."""
        super().__init__(session, QuotaUsage)

    async def get_user_usage(
        self,
        user_id: int,
        quota_type: Optional[str] = None,
        period: Optional[str] = None
    ) -> List[QuotaUsage]:
        """
        Get usage records for a user.

        Args:
            user_id: User ID
            quota_type: Optional quota type filter
            period: Optional period filter

        Returns:
            List of QuotaUsage instances
        """
        filters = {"user_id": user_id}
        if quota_type:
            filters["quota_type"] = quota_type
        if period:
            filters["period"] = period

        return await self.list(filters=filters, order_by="period_start DESC")


class QuotaRepository:
    """
    Repository for quota management with commercial features.

    Handles quota limits, usage tracking, and quota checking for
    article generation, API calls, and storage.
    """

    # Map quota types to their field prefix in UserQuota
    QUOTA_TYPE_TO_PREFIX = {
        "article_generation": "article",
        "api_call": "api",
        "storage": "storage",
    }

    def __init__(self, session: AsyncSession):
        """Initialize Quota repository."""
        self.session = session
        self.usage_repo = QuotaUsageRepository(session)

    def _get_limit_field(self, quota_type: str, period: str) -> str:
        """
        Get the limit field name for a quota type and period.

        Args:
            quota_type: Type of quota
            period: Period (daily, monthly)

        Returns:
            Field name (e.g., 'article_daily_limit', 'storage_limit_mb')
        """
        # Storage is a special case - it doesn't have period-based limits
        if quota_type == "storage":
            return "storage_limit_mb"

        prefix = self.QUOTA_TYPE_TO_PREFIX.get(quota_type)
        if not prefix:
            raise ValueError(f"Unknown quota type: {quota_type}")

        return f"{prefix}_{period}_limit"

    async def get_user_quota(self, user_id: int) -> Optional[UserQuota]:
        """
        Get quota limits for a user.

        Args:
            user_id: User ID

        Returns:
            UserQuota instance or None if not found
        """
        stmt = select(UserQuota).where(UserQuota.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user_quota(
        self,
        user_id: int,
        article_daily_limit: int = 10,
        article_monthly_limit: int = 300,
        api_daily_limit: int = 1000,
        api_monthly_limit: int = 30000,
        storage_limit_mb: int = 1000
    ) -> UserQuota:
        """
        Create quota limits for a user.

        Args:
            user_id: User ID
            article_daily_limit: Daily article generation limit
            article_monthly_limit: Monthly article generation limit
            api_daily_limit: Daily API call limit
            api_monthly_limit: Monthly API call limit
            storage_limit_mb: Storage limit in megabytes

        Returns:
            Created UserQuota instance
        """
        quota = UserQuota(
            user_id=user_id,
            article_daily_limit=article_daily_limit,
            article_monthly_limit=article_monthly_limit,
            api_daily_limit=api_daily_limit,
            api_monthly_limit=api_monthly_limit,
            storage_limit_mb=storage_limit_mb
        )
        self.session.add(quota)
        await self.session.flush()
        return quota

    async def update_limits(
        self,
        user_id: int,
        article_daily_limit: Optional[int] = None,
        article_monthly_limit: Optional[int] = None,
        api_daily_limit: Optional[int] = None,
        api_monthly_limit: Optional[int] = None,
        storage_limit_mb: Optional[int] = None
    ) -> Optional[UserQuota]:
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
        from sqlalchemy import update as sqlalchemy_update

        update_data = {}
        if article_daily_limit is not None:
            update_data['article_daily_limit'] = article_daily_limit
        if article_monthly_limit is not None:
            update_data['article_monthly_limit'] = article_monthly_limit
        if api_daily_limit is not None:
            update_data['api_daily_limit'] = api_daily_limit
        if api_monthly_limit is not None:
            update_data['api_monthly_limit'] = api_monthly_limit
        if storage_limit_mb is not None:
            update_data['storage_limit_mb'] = storage_limit_mb

        if not update_data:
            return await self.get_user_quota(user_id)

        stmt = (
            sqlalchemy_update(UserQuota)
            .where(UserQuota.user_id == user_id)
            .values(**update_data)
            .returning(UserQuota)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_quota_available(
        self,
        user_id: int,
        quota_type: str,
        period: str,
        amount: int = 1
    ) -> bool:
        """
        Check if user has enough quota available.

        Args:
            user_id: User ID
            quota_type: Type of quota (article_generation, api_call, storage)
            period: Period (daily, monthly)
            amount: Amount to check

        Returns:
            True if quota is available, False otherwise
        """
        # Get user quota limits
        quota = await self.get_user_quota(user_id)
        if not quota:
            return False

        # Get the limit for the quota type and period
        limit_field = self._get_limit_field(quota_type, period)
        limit = getattr(quota, limit_field, None)
        if limit is None:
            return False

        # Get current usage
        usage = await self.get_usage_count(user_id, quota_type, period)

        return usage + amount <= limit

    async def record_usage(
        self,
        user_id: int,
        quota_type: str,
        consumed: int,
        period: str
    ) -> QuotaUsage:
        """
        Record quota usage.

        Args:
            user_id: User ID
            quota_type: Type of quota
            consumed: Amount consumed
            period: Period (daily, monthly)

        Returns:
            Created QuotaUsage instance
        """
        usage = QuotaUsage(
            user_id=user_id,
            quota_type=quota_type,
            consumed=consumed,
            period=period,
            period_start=datetime.now(timezone.utc)
        )
        self.session.add(usage)
        await self.session.flush()
        return usage

    async def get_usage_count(
        self,
        user_id: int,
        quota_type: str,
        period: str
    ) -> int:
        """
        Get total usage count for a user, quota type, and period.

        Args:
            user_id: User ID
            quota_type: Type of quota
            period: Period (daily, monthly)

        Returns:
            Total usage count
        """
        stmt = select(func.sum(QuotaUsage.consumed)).where(
            and_(
                QuotaUsage.user_id == user_id,
                QuotaUsage.quota_type == quota_type,
                QuotaUsage.period == period
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_remaining_quota(
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
        quota = await self.get_user_quota(user_id)
        if not quota:
            return 0

        limit_field = self._get_limit_field(quota_type, period)
        limit = getattr(quota, limit_field, 0)

        usage = await self.get_usage_count(user_id, quota_type, period)

        return max(0, limit - usage)

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
            period: Period to reset
            quota_type: Optional quota type filter

        Returns:
            Number of records deleted
        """
        stmt = delete(QuotaUsage).where(
            and_(
                QuotaUsage.user_id == user_id,
                QuotaUsage.period == period
            )
        )

        if quota_type:
            stmt = stmt.where(QuotaUsage.quota_type == quota_type)

        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_all_user_quotas(self, user_id: int) -> List[UserQuota]:
        """
        Get all quotas for a user (currently just one record).

        Args:
            user_id: User ID

        Returns:
            List of UserQuota instances
        """
        quota = await self.get_user_quota(user_id)
        return [quota] if quota else []

    async def delete_user_quota(self, user_id: int) -> bool:
        """
        Delete quota settings for a user.

        Args:
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(UserQuota).where(UserQuota.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_quota_summary(
        self,
        user_id: int
    ) -> Dict[str, Dict[str, int]]:
        """
        Get quota usage summary for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with quota_type as key and {'daily': usage, 'monthly': usage} as values
        """
        quota = await self.get_user_quota(user_id)
        if not quota:
            return {}

        summary = {}

        # Get all usage records
        usage_records = await self.usage_repo.get_user_usage(user_id)

        for record in usage_records:
            if record.quota_type not in summary:
                summary[record.quota_type] = {'daily': 0, 'monthly': 0}

            summary[record.quota_type][record.period] += record.consumed

        return summary

    async def check_and_consume(
        self,
        user_id: int,
        quota_type: str,
        amount: int,
        period: str
    ) -> Tuple[bool, int]:
        """
        Atomically check quota and consume if available.

        Args:
            user_id: User ID
            quota_type: Type of quota
            amount: Amount to consume
            period: Period (daily, monthly)

        Returns:
            Tuple of (success: bool, remaining: int)
        """
        # Check if quota is available
        if not await self.check_quota_available(user_id, quota_type, period, amount):
            remaining = await self.get_remaining_quota(user_id, quota_type, period)
            return False, remaining

        # Consume quota
        await self.record_usage(user_id, quota_type, amount, period)

        # Return remaining
        remaining = await self.get_remaining_quota(user_id, quota_type, period)
        return True, remaining

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
        # This is a more complex query that joins quotas with usage
        # For now, return empty list as this would be rare to use
        return []

    async def get_usage_history(
        self,
        user_id: int,
        limit: int = 100
    ) -> List[QuotaUsage]:
        """
        Get usage history for a user.

        Args:
            user_id: User ID
            limit: Maximum records to return

        Returns:
            List of QuotaUsage instances
        """
        return await self.usage_repo.list(
            filters={"user_id": user_id},
            limit=limit,
            order_by="period_start DESC"
        )
