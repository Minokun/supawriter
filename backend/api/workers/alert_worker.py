# -*- coding: utf-8 -*-
"""
Alert Worker - 热点预警定时任务
每30分钟执行一次，扫描热点并匹配用户关键词
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from uuid import UUID

from backend.api.services.hotspots_service import hotspots_service
from backend.api.core.redis_client import redis_client

logger = logging.getLogger(__name__)

# 热点源列表
HOTSPOT_SOURCES = ['baidu', 'weibo', 'douyin', 'thepaper', '36kr']


async def get_active_keywords_grouped_by_user() -> Dict[int, List[Dict[str, Any]]]:
    """
    获取所有启用的关键词，按用户分组

    Returns:
        Dict[user_id, List[{id, keyword, category}]]
    """
    try:
        # 尝试导入 Sprint 6 模型
        from backend.api.db.models.alert import AlertKeyword
        from backend.api.db.session import get_async_db_session as get_db_session

        async with get_db_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(AlertKeyword).where(AlertKeyword.is_active == True)
            )
            keywords = result.scalars().all()

            grouped = {}
            for kw in keywords:
                if kw.user_id not in grouped:
                    grouped[kw.user_id] = []
                grouped[kw.user_id].append({
                    'id': str(kw.id),
                    'keyword': kw.keyword,
                    'category': kw.category
                })
            return grouped

    except ImportError:
        logger.warning("AlertKeyword model not found, skipping keyword matching")
        return {}
    except Exception as e:
        logger.error(f"Error fetching active keywords: {e}")
        return {}


async def get_all_hotspots_from_cache() -> List[Dict[str, Any]]:
    """
    获取所有平台的热点数据（优先从缓存）

    Returns:
        合并后的热点列表，每项包含 title, source, url 等
    """
    all_hotspots = []

    for source in HOTSPOT_SOURCES:
        try:
            # 优先从缓存获取
            cached_data = await redis_client.get_cached_hotspots(source)
            if cached_data:
                hotspots = cached_data
            else:
                # 缓存未命中，实时获取
                result = await hotspots_service.get_hotspots(source)
                if result.get('success'):
                    hotspots = result.get('data', [])
                else:
                    hotspots = []

            # 添加来源标记
            for item in hotspots:
                if isinstance(item, dict):
                    item['source'] = source
                    # 确保有 title 字段
                    if 'title' not in item and 'word' in item:
                        item['title'] = item['word']

            all_hotspots.extend(hotspots)
            logger.info(f"Fetched {len(hotspots)} hotspots from {source}")

        except Exception as e:
            logger.error(f"Error fetching hotspots from {source}: {e}")
            continue

    logger.info(f"Total hotspots collected: {len(all_hotspots)}")
    return all_hotspots


def match_keyword_with_hotspots(keyword: str, hotspots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    匹配关键词与热点标题

    Args:
        keyword: 用户关键词
        hotspots: 热点列表

    Returns:
        匹配到的热点列表
    """
    matched = []
    keyword_lower = keyword.lower()

    for hotspot in hotspots:
        if not isinstance(hotspot, dict):
            continue

        title = hotspot.get('title', '') or hotspot.get('word', '')
        if not title:
            continue

        # 简单的字符串包含匹配（不区分大小写）
        if keyword_lower in title.lower():
            matched.append(hotspot)
            continue

        # 分词匹配：关键词包含热点标题中的词
        # 例如关键词="人工智能"，热点标题="AI人工智能发展趋势"
        title_words = title.lower().split()
        for word in title_words:
            if len(word) >= 2 and word in keyword_lower:
                matched.append(hotspot)
                break

    return matched


async def alert_exists(user_id: int, keyword_id: str, hotspot_title: str) -> bool:
    """
    检查是否已存在相同的预警记录（去重）

    Args:
        user_id: 用户ID
        keyword_id: 关键词ID
        hotspot_title: 热点标题

    Returns:
        True if exists
    """
    try:
        from backend.api.db.models.alert import AlertRecord
        from backend.api.db.session import get_async_db_session as get_db_session
        from sqlalchemy import select

        async with get_db_session() as session:
            # 检查24小时内是否已存在相同匹配
            from datetime import timedelta
            time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

            result = await session.execute(
                select(AlertRecord).where(
                    AlertRecord.user_id == user_id,
                    AlertRecord.keyword_id == UUID(keyword_id),
                    AlertRecord.hotspot_title == hotspot_title,
                    AlertRecord.matched_at >= time_threshold
                )
            )
            existing = result.scalar_one_or_none()
            return existing is not None

    except ImportError:
        # 模型不存在，假设不存在记录
        return False
    except Exception as e:
        logger.error(f"Error checking alert existence: {e}")
        return False


async def create_alert_record(
    user_id: int,
    keyword_id: str,
    keyword: str,
    hotspot: Dict[str, Any]
) -> Optional[str]:
    """
    创建预警记录

    Args:
        user_id: 用户ID
        keyword_id: 关键词ID
        keyword: 关键词文本
        hotspot: 热点数据

    Returns:
        记录ID或None
    """
    try:
        from backend.api.db.models.alert import AlertRecord
        from backend.api.db.session import get_async_db_session as get_db_session
        from uuid import uuid4

        async with get_db_session() as session:
            record = AlertRecord(
                id=uuid4(),
                user_id=user_id,
                keyword_id=UUID(keyword_id),
                keyword=keyword,
                hotspot_title=hotspot.get('title', '') or hotspot.get('word', ''),
                hotspot_source=hotspot.get('source', 'unknown'),
                hotspot_url=hotspot.get('url', ''),
                hotspot_desc=hotspot.get('desc', ''),
                matched_at=datetime.now(timezone.utc),
                is_read=False
            )
            session.add(record)
            await session.commit()

            logger.info(f"Created alert record for user {user_id}, keyword '{keyword}'")
            return str(record.id)

    except ImportError:
        logger.warning("AlertRecord model not found, skipping record creation")
        return None
    except Exception as e:
        logger.error(f"Error creating alert record: {e}")
        return None


async def increment_hotspot_match_count(user_id: int) -> bool:
    """
    更新用户统计中的热点匹配数

    Args:
        user_id: 用户ID

    Returns:
        True if success
    """
    try:
        from backend.api.db.models.alert import UserStats
        from backend.api.db.session import get_async_db_session as get_db_session
        from sqlalchemy import select

        async with get_db_session() as session:
            result = await session.execute(
                select(UserStats).where(UserStats.user_id == user_id)
            )
            stats = result.scalar_one_or_none()

            if stats:
                stats.hotspot_matches = (stats.hotspot_matches or 0) + 1
                stats.updated_at = datetime.now(timezone.utc)
            else:
                # 创建新的统计记录
                stats = UserStats(
                    user_id=user_id,
                    hotspot_matches=1,
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(stats)

            await session.commit()
            logger.debug(f"Incremented hotspot match count for user {user_id}")
            return True

    except ImportError:
        logger.warning("UserStats model not found, skipping stats update")
        return False
    except Exception as e:
        logger.error(f"Error updating hotspot match count: {e}")
        return False


async def scan_hotspots_and_alert(ctx) -> Dict[str, Any]:
    """
    ARQ定时任务：扫描热点并匹配关键词

    执行频率: 每30分钟

    Args:
        ctx: ARQ context

    Returns:
        执行结果统计
    """
    logger.info("=" * 60)
    logger.info("Starting hotspot scan and alert task")
    logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    stats = {
        'users_processed': 0,
        'keywords_checked': 0,
        'alerts_created': 0,
        'errors': []
    }

    try:
        # 1. 获取所有启用的关键词（按用户分组）
        user_keywords = await get_active_keywords_grouped_by_user()
        if not user_keywords:
            logger.info("No active keywords found, task completed")
            return {'success': True, 'stats': stats}

        stats['users_processed'] = len(user_keywords)
        total_keywords = sum(len(kws) for kws in user_keywords.values())
        stats['keywords_checked'] = total_keywords

        logger.info(f"Found {len(user_keywords)} users with {total_keywords} active keywords")

        # 2. 获取各平台热点数据
        hotspots = await get_all_hotspots_from_cache()
        if not hotspots:
            logger.warning("No hotspots fetched, task completed")
            return {'success': True, 'stats': stats}

        # 3. 对每个用户的关键词进行匹配
        for user_id, keywords in user_keywords.items():
            try:
                for kw in keywords:
                    keyword_id = kw['id']
                    keyword_text = kw['keyword']

                    # 匹配热点
                    matched = match_keyword_with_hotspots(keyword_text, hotspots)

                    for hotspot in matched:
                        hotspot_title = hotspot.get('title', '') or hotspot.get('word', '')

                        # 检查是否已存在（去重）
                        if await alert_exists(user_id, keyword_id, hotspot_title):
                            logger.debug(f"Alert already exists for user {user_id}, keyword '{keyword_text}'")
                            continue

                        # 创建预警记录
                        record_id = await create_alert_record(
                            user_id=user_id,
                            keyword_id=keyword_id,
                            keyword=keyword_text,
                            hotspot=hotspot
                        )

                        if record_id:
                            stats['alerts_created'] += 1
                            # 更新用户统计
                            await increment_hotspot_match_count(user_id)

            except Exception as e:
                error_msg = f"Error processing user {user_id}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                continue

        logger.info("=" * 60)
        logger.info("Hotspot scan and alert task completed")
        logger.info(f"Stats: {stats}")
        logger.info("=" * 60)

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        logger.exception(f"Fatal error in scan_hotspots_and_alert: {e}")
        return {
            'success': False,
            'error': str(e),
            'stats': stats
        }
