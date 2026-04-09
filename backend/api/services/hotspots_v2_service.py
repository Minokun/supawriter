# -*- coding: utf-8 -*-
"""
热点服务 V2 - 基于 TrendRadar API
统一数据源，支持持久化存储和排名变化追踪

数据源优先级:
1. 本地 TrendRadar API (http://localhost:8765)
2. newsnow API (https://newsnow.busiyi.world/api/s) - 备用
"""

import os
import httpx
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.repositories.hotspot import (
    HotspotSourceRepository,
    HotspotItemRepository,
    HotspotRankHistoryRepository
)
from backend.api.core.redis_client import redis_client
from backend.api.db.models.hotspot import HotspotSource, HotspotItem

logger = logging.getLogger(__name__)

# 数据源配置
TRENDRADAR_API_URL = os.getenv("TRENDRADAR_API_URL", "http://localhost:8765")
NEWSNOW_API_URL = os.getenv("NEWSNOW_API_URL", "https://newsnow.busiyi.world/api/s")
CACHE_TTL = 300  # 5分钟缓存


@dataclass
class SyncResult:
    """同步结果"""
    source: str
    success: bool
    created: int = 0
    updated: int = 0
    total: int = 0
    error: Optional[str] = None
    items: List[Dict[str, Any]] = field(default_factory=list)


class HotspotsV2Service:
    """热点采集服务 V2 - 基于 TrendRadar API"""

    # 统一平台 ID 映射
    SOURCE_MAPPING = {
        'baidu': {'name': '百度热搜', 'icon': '🔥', 'category': '综合', 'trendradar': 'baidu'},
        'weibo': {'name': '微博热搜', 'icon': '📱', 'category': '综合', 'trendradar': 'weibo'},
        'douyin': {'name': '抖音热搜', 'icon': '🎵', 'category': '短视频', 'trendradar': 'douyin'},
        'zhihu': {'name': '知乎热榜', 'icon': '💡', 'category': '综合', 'trendradar': 'zhihu'},
        'bilibili': {'name': 'B站热榜', 'icon': '📺', 'category': '短视频', 'trendradar': 'bilibili'},
        'thepaper': {'name': '澎湃新闻', 'icon': '📰', 'category': '新闻', 'trendradar': 'thepaper'},
        '36kr': {'name': '36氪', 'icon': '💼', 'category': '科技', 'trendradar': None},  # newsnow only
        'cls': {'name': '财联社', 'icon': '💰', 'category': '财经', 'trendradar': 'cls'},
        'wallstreet': {'name': '华尔街见闻', 'icon': '📈', 'category': '财经', 'trendradar': 'wallstreetcn'},
        'toutiao': {'name': '今日头条', 'icon': '📱', 'category': '综合', 'trendradar': 'toutiao'},
        'ifeng': {'name': '凤凰网', 'icon': '🗞️', 'category': '新闻', 'trendradar': 'ifeng'},
        'tieba': {'name': '贴吧热搜', 'icon': '💬', 'category': '综合', 'trendradar': 'tieba'},
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self.source_repo = HotspotSourceRepository(session)
        self.item_repo = HotspotItemRepository(session)
        self.history_repo = HotspotRankHistoryRepository(session)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端（懒加载）"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            )
        return self._http_client

    async def close(self):
        """关闭资源"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    # ============ 数据获取 ============

    def _get_trendradar_id(self, source: str) -> Optional[str]:
        """获取平台对应的 TrendRadar ID"""
        source_info = self.SOURCE_MAPPING.get(source)
        if source_info:
            return source_info.get('trendradar')
        return None

    async def fetch_from_trendradar(self, source: str) -> Optional[List[Dict[str, Any]]]:
        """
        从本地 TrendRadar API 获取指定平台的热点数据

        Args:
            source: 平台 ID (baidu, weibo, etc.)

        Returns:
            热点列表，None 表示需要尝试备用源，空列表表示不支持
        """
        # 获取 TrendRadar 对应的源 ID
        trendradar_id = self._get_trendradar_id(source)
        if not trendradar_id:
            logger.info(f"{source} 不被 TrendRadar 支持，将使用备用源")
            return None  # 返回 None 表示需要尝试备用源

        client = await self._get_http_client()

        try:
            url = f"{TRENDRADAR_API_URL}/api/v1/latest/{trendradar_id}"
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()

            data = response.json()

            items = data.get('items', [])
            parsed_items = []

            for item in items:
                parsed = {
                    'title': item.get('title', '').strip(),
                    'url': item.get('url', ''),
                    'source_id': '',
                    'rank': item.get('rank', 0),
                    'description': item.get('description'),
                    'hot_value': item.get('hot_value'),
                    'source': source,  # 使用统一的 source ID
                }
                if parsed['title']:
                    parsed_items.append(parsed)

            logger.info(f"从 TrendRadar 获取 {source}({trendradar_id}) 热点 {len(parsed_items)} 条")
            return parsed_items

        except httpx.ConnectError:
            logger.warning(f"TrendRadar API 不可用，尝试备用数据源")
            return None  # 返回 None 表示需要尝试备用源
        except httpx.HTTPError as e:
            logger.error(f"TrendRadar API 请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析 TrendRadar 响应失败: {e}", exc_info=True)
            return None

    async def fetch_from_newsnow(self, source: str) -> List[Dict[str, Any]]:
        """
        从 newsnow API 获取指定平台的热点数据（备用）

        Args:
            source: 平台 ID (baidu, weibo, etc.)

        Returns:
            热点列表
        """
        client = await self._get_http_client()

        try:
            # newsnow API 使用查询参数格式
            url = f"{NEWSNOW_API_URL}?id={source}&latest"
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()

            data = response.json()

            if data.get('status') not in ['success', 'cache']:
                logger.error(f"newsnow API 返回错误: {data}")
                return []

            items = data.get('items', [])
            parsed_items = []

            for rank, item in enumerate(items, start=1):
                parsed = self._parse_item(item, source, rank)
                if parsed:
                    parsed_items.append(parsed)

            logger.info(f"从 newsnow 获取 {source} 热点 {len(parsed_items)} 条")
            return parsed_items

        except httpx.HTTPError as e:
            logger.error(f"获取 {source} 热点失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析 {source} 热点失败: {e}", exc_info=True)
            return []

    async def fetch_hotspots(self, source: str) -> List[Dict[str, Any]]:
        """
        获取热点数据（优先使用 TrendRadar，失败时回退到 newsnow）

        Args:
            source: 平台 ID

        Returns:
            热点列表
        """
        # 优先使用本地 TrendRadar API
        items = await self.fetch_from_trendradar(source)

        if items is None:
            # TrendRadar 不可用，尝试 newsnow
            logger.info(f"TrendRadar 不可用，使用 newsnow 作为备用源")
            items = await self.fetch_from_newsnow(source)

        return items or []

    def _parse_item(self, raw: Dict[str, Any], source: str, rank: int) -> Optional[Dict[str, Any]]:
        """
        解析 newsnow API 响应为统一格式

        Args:
            raw: API 原始数据
            source: 来源平台
            rank: 排名

        Returns:
            解析后的热点数据
        """
        try:
            title = raw.get('title', '').strip()
            if not title:
                return None

            # 获取描述
            description = None
            extra = raw.get('extra', {})
            if extra:
                description = extra.get('hover', '')

            return {
                'title': title,
                'url': raw.get('url', ''),
                'source_id': raw.get('id', ''),
                'rank': rank,
                'description': description,
                'hot_value': None,  # newsnow API 不提供热度值
                'source': source,
            }

        except Exception as e:
            logger.error(f"解析热点失败: {e}")
            return None

    # ============ 同步逻辑 ============

    async def sync_source(self, source: str) -> SyncResult:
        """
        同步单个平台的热点数据

        流程：
        1. 从 TrendRadar/newsnow API 获取数据
        2. 对比数据库现有数据
        3. 更新/创建热点条目
        4. 记录排名历史

        Args:
            source: 平台 ID

        Returns:
            SyncResult 同步结果
        """
        result = SyncResult(source=source, success=False)

        try:
            # 1. 获取数据（优先 TrendRadar，备用 newsnow）
            items = await self.fetch_hotspots(source)
            if not items:
                result.error = "获取数据为空"
                return result

            result.items = items

            # 2. 批量 upsert
            upsert_result = await self.item_repo.bulk_upsert(items, source)
            result.created = upsert_result['created']
            result.updated = upsert_result['updated']
            result.total = upsert_result['total']

            # 3. 标记不在榜单中的热点
            current_titles = [item['title'] for item in items]
            stale_count = await self.item_repo.mark_stale_items(source, current_titles)
            if stale_count:
                logger.info(f"{source} 有 {stale_count} 条热点下榜")

            # 4. 提交事务
            await self.session.commit()

            # 5. 更新缓存 - 从数据库获取正确格式的数据
            db_items = await self.item_repo.get_latest_by_source(source, 50)
            if db_items:
                cache_items = [self._item_to_dict(item) for item in db_items]
                await redis_client.cache_hotspots(f"v2:{source}", cache_items, CACHE_TTL)

            result.success = True
            logger.info(f"{source} 同步完成: 新增 {result.created}, 更新 {result.updated}")

        except Exception as e:
            await self.session.rollback()
            result.error = str(e)
            logger.error(f"{source} 同步失败: {e}", exc_info=True)

        return result

    async def sync_all_sources(self) -> Dict[str, SyncResult]:
        """
        同步所有启用的平台

        Returns:
            各平台同步结果
        """
        results = {}

        # 获取启用的平台
        sources = await self.source_repo.get_enabled_sources()

        if not sources:
            # 如果数据库没有配置，使用默认平台
            logger.info("使用默认平台配置")
            default_sources = ['baidu', 'weibo', 'douyin', 'zhihu', 'bilibili',
                               'thepaper', 'toutiao', 'cls', 'wallstreet', '36kr',
                               'ifeng', 'tieba']  # 12个平台，移除不支持的netease
            for source_id in default_sources:
                result = await self.sync_source(source_id)
                results[source_id] = result
        else:
            for source in sources:
                result = await self.sync_source(source.id)
                results[source.id] = result

        return results

    # ============ 查询接口 ============

    def _item_to_dict(self, item: HotspotItem) -> Dict[str, Any]:
        """Convert HotspotItem model to dict for serialization"""
        return {
            'id': item.id,
            'title': item.title,
            'url': item.url,
            'source': item.source,
            'source_id': item.source_id,
            'rank': item.rank,
            'rank_prev': item.rank_prev,
            'rank_change': item.rank_change,
            'hot_value': item.hot_value,
            'hot_value_prev': item.hot_value_prev,
            'is_new': item.is_new,
            'description': item.description,
            'icon_url': item.icon_url,
            'mobile_url': item.mobile_url,
            'published_at': item.published_at.isoformat() if item.published_at else None,
            'created_at': item.created_at.isoformat() if item.created_at else None,
            'updated_at': item.updated_at.isoformat() if item.updated_at else None,
        }

    async def get_latest_by_source(
        self,
        source: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取指定平台的最新热点"""
        # 先尝试从缓存获取
        cached = await redis_client.get_cached_hotspots(f"v2:{source}")
        if cached:
            return cached

        # 从数据库获取
        items = await self.item_repo.get_latest_by_source(source, limit)

        # 转换为字典格式
        result = [self._item_to_dict(item) for item in items]

        # 更新缓存
        if result:
            await redis_client.cache_hotspots(f"v2:{source}", result, CACHE_TTL)

        return result

    async def get_all_latest(self, limit_per_source: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有平台的最新热点"""
        sources = await self.source_repo.get_enabled_sources()
        result = {}

        for source in sources:
            items = await self.get_latest_by_source(source.id, limit_per_source)
            result[source.id] = items

        return result

    async def get_rank_history(
        self,
        hotspot_id: int,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """获取热点排名历史"""
        history = await self.history_repo.get_rank_history(hotspot_id, hours)
        return [
            {
                'rank': h.rank,
                'hot_value': h.hot_value,
                'is_new': h.is_new,
                'recorded_at': h.recorded_at.isoformat()
            }
            for h in history
        ]

    # ============ 平台管理 ============

    async def get_sources(self) -> List[Dict[str, Any]]:
        """获取所有平台配置"""
        sources = await self.source_repo.get_enabled_sources()

        if not sources:
            # 返回默认配置
            return [
                {
                    'id': sid,
                    'name': info['name'],
                    'icon': info['icon'],
                    'category': info['category'],
                    'enabled': True
                }
                for sid, info in self.SOURCE_MAPPING.items()
            ]

        return [
            {
                'id': s.id,
                'name': s.name,
                'icon': s.icon,
                'category': s.category,
                'enabled': s.enabled
            }
            for s in sources
        ]

    async def init_sources(self) -> int:
        """初始化平台配置（从默认配置创建）"""
        created = 0
        for source_id, info in self.SOURCE_MAPPING.items():
            existing = await self.source_repo.get_by_id(source_id)
            if not existing:
                await self.source_repo.create(
                    id=source_id,
                    name=info['name'],
                    icon=info['icon'],
                    category=info['category'],
                    enabled=True,
                    sort_order=created
                )
                created += 1

        await self.session.commit()
        logger.info(f"初始化 {created} 个平台配置")
        return created

    # ============ 缓存管理 ============

    async def clear_cache(self, source: Optional[str] = None):
        """清除缓存"""
        if source:
            await redis_client.async_client.delete(f"hotspots:v2:{source}")
        else:
            # 清除所有热点缓存
            keys = await redis_client.async_client.keys("hotspots:v2:*")
            if keys:
                await redis_client.async_client.delete(*keys)


# 便捷函数
async def get_hotspots_v2_service(session: AsyncSession) -> HotspotsV2Service:
    """获取热点服务实例"""
    return HotspotsV2Service(session)