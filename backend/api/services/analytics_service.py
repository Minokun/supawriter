"""Analytics service for user statistics and dashboard data."""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.api.db.models.alert import UserStats
from backend.api.db.models.article import Article
from backend.api.repositories.base import BaseRepository


class AnalyticsService:
    """User statistics aggregation service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats_repo = BaseRepository(session, UserStats)

    async def get_user_stats(self, user_id: int, tier: str) -> Dict[str, Any]:
        """Get user statistics based on membership tier.

        Args:
            user_id: User ID
            tier: Membership tier (free, pro, ultra)

        Returns:
            Stats dict with tier-appropriate fields
        """
        # Get or create user stats
        stats = await self.stats_repo.get_by_field("user_id", user_id)
        if not stats:
            stats = await self._create_initial_stats(user_id)

        # Build response based on tier
        result = {
            "total_articles": stats.total_articles,
            "total_words": stats.total_words,
            "monthly_articles": stats.monthly_articles,
            "quota_used": stats.quota_used,
            "quota_total": stats.quota_total,
        }

        if tier in ["pro", "ultra", "superuser"]:
            result.update({
                "avg_score": stats.avg_score,
                "score_history": stats.score_history or [],
                "platform_stats": stats.platform_stats or {},
            })

        if tier in ["ultra", "superuser"]:
            result.update({
                "hotspot_matches": stats.hotspot_matches,
                "keyword_hit_rate": stats.keyword_hit_rate,
                "model_usage": stats.model_usage or {},
            })

        return result

    async def refresh_user_stats(self, user_id: int) -> UserStats:
        """Refresh user statistics from source data."""
        # Calculate article stats
        article_stats = await self._calculate_article_stats(user_id)

        # Get existing stats or create new
        stats = await self.stats_repo.get_by_field("user_id", user_id)

        update_data = {
            "total_articles": article_stats["total"],
            "total_words": article_stats["total_words"],
            "monthly_articles": article_stats["monthly"],
            "updated_at": datetime.now(timezone.utc),
        }

        if stats:
            stats = await self.stats_repo.update(stats.user_id, **update_data)
        else:
            update_data["user_id"] = user_id
            stats = await self.stats_repo.create(**update_data)

        return stats

    async def _create_initial_stats(self, user_id: int) -> UserStats:
        """Create initial stats record for user."""
        # Get quota info
        from backend.api.db.models.quota import UserQuota
        quota_result = await self.session.execute(
            select(UserQuota.article_monthly_limit).where(UserQuota.user_id == user_id)
        )
        quota_total = quota_result.scalar_one_or_none() or 0

        # Calculate article stats
        article_stats = await self._calculate_article_stats(user_id)

        return await self.stats_repo.create(
            user_id=user_id,
            total_articles=article_stats["total"],
            total_words=article_stats["total_words"],
            monthly_articles=article_stats["monthly"],
            quota_used=article_stats["monthly"],
            quota_total=quota_total,
            hotspot_matches=0,
        )

    async def _calculate_article_stats(self, user_id: int) -> Dict[str, int]:
        """Calculate article statistics from source."""
        # Total articles
        stmt = select(func.count()).where(Article.user_id == user_id)
        result = await self.session.execute(stmt)
        total = result.scalar() or 0

        # Total words
        stmt = select(func.sum(Article.word_count)).where(Article.user_id == user_id)
        result = await self.session.execute(stmt)
        total_words = result.scalar() or 0

        # Monthly articles (current month)
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stmt = select(func.count()).where(
            and_(
                Article.user_id == user_id,
                Article.created_at >= month_start
            )
        )
        result = await self.session.execute(stmt)
        monthly = result.scalar() or 0

        return {
            "total": total,
            "total_words": total_words,
            "monthly": monthly,
        }

    async def update_article_stats(self, user_id: int, word_count: int):
        """Update stats after article generation (incremental)."""
        stats = await self.stats_repo.get_by_field("user_id", user_id)

        if stats:
            stats.total_articles += 1
            stats.total_words += word_count
            stats.monthly_articles += 1
            stats.quota_used += 1
            stats.updated_at = datetime.now(timezone.utc)
        else:
            await self._create_initial_stats(user_id)

    async def update_score_stats(self, user_id: int, new_score: float):
        """Update score statistics after article scoring."""
        stats = await self.stats_repo.get_by_field("user_id", user_id)

        if not stats:
            stats = await self._create_initial_stats(user_id)

        # Update average score
        current_avg = stats.avg_score or 0
        total_articles = stats.total_articles or 1
        new_avg = (current_avg * (total_articles - 1) + new_score) / total_articles
        stats.avg_score = round(new_avg, 2)

        # Update score history
        history = stats.score_history or []
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")

        # Find or create entry for current month
        month_entry = next((h for h in history if h.get("date") == current_month), None)
        if month_entry:
            # Update average for the month
            old_count = month_entry.get("count", 1)
            old_avg = month_entry.get("score", 0)
            month_entry["score"] = round((old_avg * old_count + new_score) / (old_count + 1), 2)
            month_entry["count"] = old_count + 1
        else:
            history.append({
                "date": current_month,
                "score": round(new_score, 2),
                "count": 1
            })

        # Keep only last 12 months
        history = sorted(history, key=lambda x: x.get("date", ""), reverse=True)[:12]
        stats.score_history = history
        stats.updated_at = datetime.now(timezone.utc)

    async def update_platform_stats(self, user_id: int, platform: str):
        """Update platform distribution stats."""
        stats = await self.stats_repo.get_by_field("user_id", user_id)

        if not stats:
            stats = await self._create_initial_stats(user_id)

        platform_stats = stats.platform_stats or {}
        platform_stats[platform] = platform_stats.get(platform, 0) + 1
        stats.platform_stats = platform_stats
        stats.updated_at = datetime.now(timezone.utc)

    async def update_model_usage(self, user_id: int, model: str):
        """Update model usage stats (Ultra tier)."""
        stats = await self.stats_repo.get_by_field("user_id", user_id)

        if not stats:
            stats = await self._create_initial_stats(user_id)

        model_usage = stats.model_usage or {}
        model_usage[model] = model_usage.get(model, 0) + 1
        stats.model_usage = model_usage
        stats.updated_at = datetime.now(timezone.utc)

    async def calculate_keyword_hit_rate(self, user_id: int) -> float:
        """Calculate keyword hit rate for user."""
        from backend.api.db.models.alert import AlertKeyword, AlertRecord

        # Get keyword count
        stmt = select(func.count()).where(
            and_(
                AlertKeyword.user_id == user_id,
                AlertKeyword.is_active == True
            )
        )
        result = await self.session.execute(stmt)
        keyword_count = result.scalar() or 0

        if keyword_count == 0:
            return 0.0

        # Get match count (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = select(func.count()).where(
            and_(
                AlertRecord.user_id == user_id,
                AlertRecord.matched_at >= thirty_days_ago
            )
        )
        result = await self.session.execute(stmt)
        match_count = result.scalar() or 0

        # Calculate hit rate (matches per keyword per month, capped at 100%)
        hit_rate = min(100.0, (match_count / keyword_count) * 100)

        # Update stats
        stats = await self.stats_repo.get_by_field("user_id", user_id)
        if stats:
            stats.keyword_hit_rate = round(hit_rate, 2)

        return round(hit_rate, 2)

    async def refresh_all_stats(self) -> int:
        """Refresh statistics for all users.

        Returns:
            Number of users refreshed
        """
        from backend.api.db.models.user import User

        stmt = select(User.id)
        result = await self.session.execute(stmt)
        user_ids = result.scalars().all()

        count = 0
        for user_id in user_ids:
            await self.refresh_user_stats(user_id)
            count += 1

        return count
