# -*- coding: utf-8 -*-
"""Repository layer for hotspot data operations."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from backend.api.repositories.base import BaseRepository
from backend.api.db.models.hotspot import HotspotItem, HotspotRankHistory, HotspotSource


class HotspotSourceRepository(BaseRepository[HotspotSource]):
    """Repository for hotspot source (platform) operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, HotspotSource)

    async def get_enabled_sources(self) -> List[HotspotSource]:
        """Get all enabled sources ordered by sort_order."""
        stmt = (
            select(HotspotSource)
            .where(HotspotSource.enabled == True)
            .order_by(HotspotSource.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, source_id: str) -> Optional[HotspotSource]:
        """Get source by ID."""
        stmt = select(HotspotSource).where(HotspotSource.id == source_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class HotspotItemRepository(BaseRepository[HotspotItem]):
    """Repository for hotspot item operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, HotspotItem)

    async def get_latest_by_source(
        self,
        source: str,
        limit: int = 50
    ) -> List[HotspotItem]:
        """Get latest hotspot items for a source, ordered by rank."""
        stmt = (
            select(HotspotItem)
            .where(HotspotItem.source == source)
            .order_by(HotspotItem.rank)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_title_source(
        self,
        title: str,
        source: str
    ) -> Optional[HotspotItem]:
        """Get hotspot by title and source (unique constraint)."""
        stmt = select(HotspotItem).where(
            and_(
                HotspotItem.title == title,
                HotspotItem.source == source
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source_id(
        self,
        source_id: str,
        source: str
    ) -> Optional[HotspotItem]:
        """Get hotspot by platform internal ID and source."""
        stmt = select(HotspotItem).where(
            and_(
                HotspotItem.source_id == source_id,
                HotspotItem.source == source
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_rank(
        self,
        item_id: int,
        new_rank: int,
        new_hot_value: Optional[int] = None
    ) -> Optional[HotspotItem]:
        """Update rank and track changes."""
        # Get current item
        item = await self.get_by_id(item_id)
        if not item:
            return None

        # Calculate rank change
        rank_change = (item.rank - new_rank) if new_rank else 0  # positive means rank improved

        update_data = {
            'rank_prev': item.rank,
            'rank': new_rank,
            'rank_change': rank_change,
            'is_new': False,
            'updated_at': datetime.now(timezone.utc)
        }

        if new_hot_value is not None:
            update_data['hot_value_prev'] = item.hot_value
            update_data['hot_value'] = new_hot_value

        stmt = (
            update(HotspotItem)
            .where(HotspotItem.id == item_id)
            .values(**update_data)
            .returning(HotspotItem)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_history(
        self,
        item_data: Dict[str, Any],
        record_history: bool = True
    ) -> HotspotItem:
        """Create a new hotspot item and optionally record history."""
        item = await self.create(**item_data)

        if record_history:
            history = HotspotRankHistory(
                hotspot_item_id=item.id,
                source=item.source,
                rank=item.rank,
                hot_value=item.hot_value,
                is_new=item.is_new
            )
            self.session.add(history)

        return item

    async def bulk_upsert(
        self,
        items: List[Dict[str, Any]],
        source: str
    ) -> Dict[str, Any]:
        """
        Bulk upsert hotspot items.
        Returns stats about created/updated items.
        """
        created = 0
        updated = 0
        history_records = []

        for item_data in items:
            existing = await self.get_by_title_source(item_data['title'], source)

            if existing:
                # Update existing item
                rank_change = existing.rank - item_data['rank'] if item_data.get('rank') else 0

                existing.rank_prev = existing.rank
                existing.rank = item_data.get('rank', existing.rank)
                existing.rank_change = rank_change
                existing.is_new = False

                if item_data.get('hot_value') is not None:
                    existing.hot_value_prev = existing.hot_value
                    existing.hot_value = item_data['hot_value']

                if item_data.get('url'):
                    existing.url = item_data['url']
                if item_data.get('description'):
                    existing.description = item_data['description']

                existing.updated_at = datetime.now(timezone.utc)

                # Record history
                history_records.append(HotspotRankHistory(
                    hotspot_item_id=existing.id,
                    source=source,
                    rank=existing.rank,
                    hot_value=existing.hot_value,
                    is_new=False
                ))
                updated += 1
            else:
                # Create new item
                item_data['source'] = source
                item_data['is_new'] = True
                new_item = await self.create(**item_data)

                # Record history
                history_records.append(HotspotRankHistory(
                    hotspot_item_id=new_item.id,
                    source=source,
                    rank=new_item.rank,
                    hot_value=new_item.hot_value,
                    is_new=True
                ))
                created += 1

        # Bulk insert history records
        if history_records:
            self.session.add_all(history_records)

        return {
            'created': created,
            'updated': updated,
            'total': created + updated
        }

    async def mark_stale_items(
        self,
        source: str,
        current_titles: List[str]
    ) -> int:
        """
        Mark items as stale (not in current top list).
        Returns count of items marked.
        """
        # Find items that are no longer in the top list
        stmt = (
            update(HotspotItem)
            .where(
                and_(
                    HotspotItem.source == source,
                    HotspotItem.title.notin_(current_titles)
                )
            )
            .values(rank=999, rank_change=0)  # Use 999 as "off list" marker
        )
        result = await self.session.execute(stmt)
        return result.rowcount


class HotspotRankHistoryRepository(BaseRepository[HotspotRankHistory]):
    """Repository for hotspot rank history operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, HotspotRankHistory)

    async def get_rank_history(
        self,
        hotspot_item_id: int,
        hours: int = 24
    ) -> List[HotspotRankHistory]:
        """Get rank history for a hotspot item within specified hours."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(HotspotRankHistory)
            .where(
                and_(
                    HotspotRankHistory.hotspot_item_id == hotspot_item_id,
                    HotspotRankHistory.recorded_at >= since
                )
            )
            .order_by(HotspotRankHistory.recorded_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_source_history(
        self,
        source: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[HotspotRankHistory]:
        """Get history records for a source within specified hours."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(HotspotRankHistory)
            .where(
                and_(
                    HotspotRankHistory.source == source,
                    HotspotRankHistory.recorded_at >= since
                )
            )
            .order_by(HotspotRankHistory.recorded_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_old_history(self, days: int = 7) -> int:
        """Delete history records older than specified days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = delete(HotspotRankHistory).where(
            HotspotRankHistory.recorded_at < cutoff
        )
        result = await self.session.execute(stmt)
        return result.rowcount