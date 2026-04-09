"""Alert service for hotspot matching and keyword management."""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import random

from backend.api.db.models.alert import AlertKeyword, AlertRecord, UserStats
from backend.api.db.models.article import Article
from backend.api.repositories.base import BaseRepository


class AlertService:
    """Hotspot alert matching engine."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.keyword_repo = BaseRepository(session, AlertKeyword)
        self.record_repo = BaseRepository(session, AlertRecord)
        self.stats_repo = BaseRepository(session, UserStats)

    async def add_keyword(self, user_id: int, keyword: str, category: Optional[str] = None) -> AlertKeyword:
        """Add a new alert keyword for user."""
        keyword_data = {
            "user_id": user_id,
            "keyword": keyword.strip(),
            "category": category.strip() if category else None,
            "is_active": True
        }
        return await self.keyword_repo.create(**keyword_data)

    async def remove_keyword(self, keyword_id: UUID) -> bool:
        """Remove a keyword by ID."""
        return await self.keyword_repo.delete(keyword_id)

    async def get_user_keywords(self, user_id: int, active_only: bool = False) -> List[AlertKeyword]:
        """Get all keywords for a user."""
        filters = {"user_id": user_id}
        if active_only:
            filters["is_active"] = True
        return await self.keyword_repo.list(filters=filters, order_by="created_at DESC")

    async def toggle_keyword(self, keyword_id: UUID, is_active: bool) -> Optional[AlertKeyword]:
        """Toggle keyword active status."""
        return await self.keyword_repo.update(keyword_id, is_active=is_active)

    async def get_keyword_count(self, user_id: int) -> int:
        """Get total keyword count for user."""
        return await self.keyword_repo.count({"user_id": user_id})

    async def suggest_keywords(self, user_id: int, limit: int = 5) -> List[str]:
        """AI suggest keywords based on user article history."""
        # Get user's recent articles
        stmt = select(Article).where(
            Article.user_id == user_id
        ).order_by(Article.created_at.desc()).limit(20)

        result = await self.session.execute(stmt)
        articles = result.scalars().all()

        if not articles:
            # Return default suggestions if no articles
            return ["人工智能", "科技趋势", "创业", "产品设计", "数字化转型"][:limit]

        # Extract titles and analyze common words
        titles = [a.title for a in articles if a.title]

        # Simple keyword extraction (in production, use NLP/LLM)
        common_keywords = self._extract_keywords_from_titles(titles)

        # Get existing keywords to avoid duplicates
        existing = await self.get_user_keywords(user_id)
        existing_set = {k.keyword.lower() for k in existing}

        # Filter out existing keywords
        suggestions = [k for k in common_keywords if k.lower() not in existing_set]

        return suggestions[:limit]

    def _extract_keywords_from_titles(self, titles: List[str]) -> List[str]:
        """Extract potential keywords from article titles."""
        # Common tech/business keywords in Chinese
        keyword_pool = [
            "人工智能", "AI", "机器学习", "深度学习", "大模型", "ChatGPT",
            "区块链", "Web3", "元宇宙", "NFT", "加密货币",
            "云计算", "边缘计算", "容器化", "微服务", "DevOps",
            "数字化转型", "企业架构", "敏捷开发", "产品管理",
            "用户体验", "UI设计", "交互设计", "设计系统",
            "数据分析", "大数据", "数据仓库", "商业智能",
            "创业", "融资", "商业模式", "市场策略", "增长黑客",
            "社交媒体", "内容营销", "私域流量", "社群运营",
            "新能源", "电动汽车", "自动驾驶", "碳中和", "可持续发展",
            "生物科技", "医疗健康", "基因编辑", "合成生物学"
        ]

        # Count occurrences in titles
        keyword_scores = {}
        for title in titles:
            title_lower = title.lower()
            for keyword in keyword_pool:
                if keyword.lower() in title_lower:
                    keyword_scores[keyword] = keyword_scores.get(keyword, 0) + 1

        # Sort by frequency and return
        sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)

        # If no matches from pool, return random selection
        if not sorted_keywords:
            return random.sample(keyword_pool, min(5, len(keyword_pool)))

        return [k[0] for k in sorted_keywords]

    async def scan_and_match(self, hotspots: List[Dict[str, Any]]) -> int:
        """Scan hotspots and match against active keywords.

        Args:
            hotspots: List of hotspot dicts with title, source, url, id

        Returns:
            Number of new alerts created
        """
        # Get all active keywords grouped by user
        stmt = select(AlertKeyword).where(AlertKeyword.is_active == True)
        result = await self.session.execute(stmt)
        all_keywords = result.scalars().all()

        if not all_keywords or not hotspots:
            return 0

        # Group keywords by user
        user_keywords: Dict[int, List[AlertKeyword]] = {}
        for kw in all_keywords:
            if kw.user_id not in user_keywords:
                user_keywords[kw.user_id] = []
            user_keywords[kw.user_id].append(kw)

        new_alerts = 0

        for user_id, keywords in user_keywords.items():
            for keyword in keywords:
                for hotspot in hotspots:
                    if self._match_keyword(keyword.keyword, hotspot.get("title", "")):
                        # Check if alert already exists
                        if not await self._alert_exists(
                            user_id, keyword.id, hotspot.get("id", "")
                        ):
                            await self._create_alert_record(user_id, keyword.id, hotspot)
                            new_alerts += 1

        return new_alerts

    def _match_keyword(self, keyword: str, title: str) -> bool:
        """Check if keyword matches hotspot title."""
        keyword_lower = keyword.lower().strip()
        title_lower = title.lower().strip()

        # Simple substring match (case-insensitive)
        if keyword_lower in title_lower:
            return True

        # TODO: Implement more sophisticated matching (fuzzy match, word segmentation)
        return False

    async def _alert_exists(self, user_id: int, keyword_id: UUID, hotspot_id: str) -> bool:
        """Check if alert record already exists."""
        stmt = select(func.count()).where(
            and_(
                AlertRecord.user_id == user_id,
                AlertRecord.keyword_id == keyword_id,
                AlertRecord.hotspot_id == hotspot_id
            )
        )
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def _create_alert_record(
        self,
        user_id: int,
        keyword_id: UUID,
        hotspot: Dict[str, Any]
    ) -> AlertRecord:
        """Create a new alert record."""
        record_data = {
            "user_id": user_id,
            "keyword_id": keyword_id,
            "hotspot_title": hotspot.get("title", ""),
            "hotspot_source": hotspot.get("source", "unknown"),
            "hotspot_url": hotspot.get("url"),
            "hotspot_id": hotspot.get("id"),
            "is_read": False
        }
        record = await self.record_repo.create(**record_data)

        # Increment user's hotspot match count
        await self._increment_hotspot_match(user_id)

        return record

    async def _increment_hotspot_match(self, user_id: int):
        """Increment hotspot match count in user stats."""
        stats = await self.stats_repo.get_by_field("user_id", user_id)
        if stats:
            stats.hotspot_matches += 1
            stats.updated_at = datetime.now(timezone.utc)
        else:
            # Create new stats record
            await self.stats_repo.create(
                user_id=user_id,
                hotspot_matches=1
            )

    async def get_unread_count(self, user_id: int) -> int:
        """Get unread alert count for user."""
        return await self.record_repo.count({
            "user_id": user_id,
            "is_read": False
        })

    async def get_notifications(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False
    ) -> List[AlertRecord]:
        """Get paginated notifications for user."""
        filters = {"user_id": user_id}
        if unread_only:
            filters["is_read"] = False

        offset = (page - 1) * limit
        return await self.record_repo.list(
            filters=filters,
            offset=offset,
            limit=limit,
            order_by="matched_at DESC"
        )

    async def mark_as_read(self, notification_id: UUID) -> Optional[AlertRecord]:
        """Mark a notification as read."""
        return await self.record_repo.update(notification_id, is_read=True)

    async def mark_all_read(self, user_id: int) -> int:
        """Mark all notifications as read for user."""
        from sqlalchemy import update

        stmt = (
            update(AlertRecord)
            .where(
                and_(
                    AlertRecord.user_id == user_id,
                    AlertRecord.is_read == False
                )
            )
            .values(is_read=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def delete_notification(self, notification_id: UUID) -> bool:
        """Delete a notification."""
        return await self.record_repo.delete(notification_id)
