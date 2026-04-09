# -*- coding: utf-8 -*-
"""
Hotspots Sync Worker - 热点数据同步定时任务
每10分钟从 newsnow API 同步热点数据到数据库
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def sync_hotspots_task(ctx) -> Dict[str, Any]:
    """
    ARQ定时任务：从 newsnow API 同步热点数据

    执行频率: 每10分钟

    Args:
        ctx: ARQ context

    Returns:
        执行结果统计
    """
    logger.info("=" * 60)
    logger.info("Starting hotspots sync task (newsnow API)")
    logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    stats = {
        'sources_synced': 0,
        'total_created': 0,
        'total_updated': 0,
        'errors': []
    }

    try:
        # Import here to avoid circular imports
        from backend.api.db.session import get_async_db_session
        from backend.api.services.hotspots_v2_service import HotspotsV2Service

        async with get_async_db_session() as session:
            service = HotspotsV2Service(session)

            # Sync all enabled sources
            results = await service.sync_all_sources()

            for source, result in results.items():
                if result.success:
                    stats['sources_synced'] += 1
                    stats['total_created'] += result.created
                    stats['total_updated'] += result.updated
                    logger.info(
                        f"Synced {source}: created={result.created}, updated={result.updated}"
                    )
                else:
                    error_msg = f"{source}: {result.error}"
                    stats['errors'].append(error_msg)
                    logger.error(f"Failed to sync {source}: {result.error}")

            # Close the service
            await service.close()

        logger.info("=" * 60)
        logger.info("Hotspots sync task completed")
        logger.info(f"Stats: {stats}")
        logger.info("=" * 60)

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        logger.exception(f"Fatal error in sync_hotspots_task: {e}")
        stats['errors'].append(str(e))
        return {
            'success': False,
            'error': str(e),
            'stats': stats
        }


async def cleanup_hotspot_history(ctx) -> Dict[str, Any]:
    """
    ARQ定时任务：清理过期的排名历史记录

    执行频率: 每天凌晨2点

    Args:
        ctx: ARQ context

    Returns:
        执行结果
    """
    logger.info("=" * 60)
    logger.info("Starting hotspot history cleanup task")
    logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    try:
        from backend.api.db.session import get_async_db_session
        from backend.api.repositories.hotspot import HotspotRankHistoryRepository

        async with get_async_db_session() as session:
            history_repo = HotspotRankHistoryRepository(session)
            deleted = await history_repo.cleanup_old_history(days=7)
            await session.commit()

        logger.info(f"Deleted {deleted} old history records")

        return {
            'success': True,
            'deleted': deleted
        }

    except Exception as e:
        logger.exception(f"Error in cleanup_hotspot_history: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def init_hotspot_sources(ctx) -> Dict[str, Any]:
    """
    ARQ任务：初始化平台配置

    在 worker 启动时调用一次

    Args:
        ctx: ARQ context

    Returns:
        执行结果
    """
    logger.info("Initializing hotspot sources...")

    try:
        from backend.api.db.session import get_async_db_session
        from backend.api.services.hotspots_v2_service import HotspotsV2Service

        async with get_async_db_session() as session:
            service = HotspotsV2Service(session)
            created = await service.init_sources()
            await session.commit()

        logger.info(f"Initialized {created} hotspot sources")
        return {'success': True, 'created': created}

    except Exception as e:
        logger.error(f"Failed to initialize hotspot sources: {e}")
        return {'success': False, 'error': str(e)}