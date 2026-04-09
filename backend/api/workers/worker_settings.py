# -*- coding: utf-8 -*-
"""
arq Worker Configuration
"""

import logging
from pathlib import Path
from arq import cron
from arq.connections import RedisSettings

from backend.api.config import settings

Path("logs").mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/worker.log'),
        logging.StreamHandler()
    ]
)

# Worker functions to import - import the actual function
from backend.api.workers.article_worker import generate_article_task
from backend.api.workers.alert_worker import scan_hotspots_and_alert
from backend.api.workers.stats_refresh_worker import refresh_all_user_stats
from backend.api.workers.batch_worker import process_batch_job, generate_single_article
from backend.api.workers.agent_worker import (
    scan_hotspots_for_agents,
    generate_draft_for_hotspot,
    reset_agent_daily_counters
)
from backend.api.workers.hotspots_worker import (
    sync_hotspots_task,
    cleanup_hotspot_history
)
from backend.api.core.faiss_cache import cleanup_expired_faiss_indexes

FUNCTIONS = [
    generate_article_task,
    scan_hotspots_and_alert,
    refresh_all_user_stats,
    process_batch_job,
    generate_single_article,
    scan_hotspots_for_agents,
    generate_draft_for_hotspot,
    reset_agent_daily_counters,
    sync_hotspots_task,
    cleanup_hotspot_history,
]

# Cron jobs - 定期任务
# 每小时执行一次（分钟=0）- 清理过期 FAISS 索引
# 每30分钟执行一次 - 扫描热点并匹配关键词/Agent扫描
# 每10分钟执行一次 - 同步热点数据到数据库 (newsnow API)
# 每小时执行一次（分钟=5）- 刷新所有用户统计
# 每天凌晨0点 - 重置Agent每日计数器
# 每天凌晨2点 - 清理过期排名历史
CRON_TASKS = [
    cron(cleanup_expired_faiss_indexes, minute=0, name="cleanup_faiss_indexes"),
    cron(scan_hotspots_and_alert, minute={0, 30}, name="scan_hotspots_and_alert"),  # 每30分钟
    cron(scan_hotspots_for_agents, minute={0, 30}, name="scan_hotspots_for_agents"),  # 每30分钟
    cron(sync_hotspots_task, minute={0, 10, 20, 30, 40, 50}, name="sync_hotspots_task"),  # 每10分钟
    cron(refresh_all_user_stats, minute=5, name="refresh_all_user_stats"),  # 每小时第5分钟
    cron(reset_agent_daily_counters, hour=0, minute=0, name="reset_agent_daily_counters"),  # 每天凌晨0点
    cron(cleanup_hotspot_history, hour=2, minute=0, name="cleanup_hotspot_history"),  # 每天凌晨2点
]

# Redis settings
redis_settings = RedisSettings(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    database=settings.REDIS_DB,
)

# Worker settings
class WorkerSettings:
    functions = FUNCTIONS
    cron_jobs = CRON_TASKS
    redis_settings = redis_settings
    max_jobs = 3  # Max concurrent article generation tasks
    job_timeout = 600  # 10 minutes timeout
    keep_result = 3600  # Keep results for 1 hour
    queue_read_limit = 10
    queue_name = 'arq:queue'

    # Optional: health check endpoint
    async def health_check(ctx):
        return {'status': 'healthy'}

    # Optional: on startup
    async def on_startup(ctx):
        logger = logging.getLogger(__name__)
        logger.info("=" * 60)
        logger.info("SupaWriter Worker starting...")
        logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        logger.info(f"Max concurrent jobs: 3")
        logger.info(f"Job timeout: 600s")
        logger.info("Cron jobs:")
        logger.info("  - cleanup_faiss_indexes: hourly")
        logger.info("  - scan_hotspots_and_alert: every 30 minutes")
        logger.info("  - scan_hotspots_for_agents: every 30 minutes")
        logger.info("  - sync_hotspots_task: every 10 minutes (newsnow API)")
        logger.info("  - refresh_all_user_stats: hourly")
        logger.info("  - reset_agent_daily_counters: daily at 00:00")
        logger.info("  - cleanup_hotspot_history: daily at 02:00")
        logger.info("=" * 60)

    # Optional: on shutdown
    async def on_shutdown(ctx):
        logger = logging.getLogger(__name__)
        logger.info("Article Generator Worker shutting down...")
        logger.info("=" * 60)
