# -*- coding: utf-8 -*-
"""
Stats Refresh Worker - 用户统计数据刷新定时任务
每小时执行一次，刷新所有用户统计数据
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID

logger = logging.getLogger(__name__)


async def get_all_active_users() -> List[Dict[str, Any]]:
    """
    获取所有活跃用户

    Returns:
        用户列表，每项包含 id, username 等
    """
    try:
        from backend.api.db.models.user import User
        from backend.api.db.session import get_async_db_session as get_db_session
        from sqlalchemy import select

        async with get_db_session() as session:
            result = await session.execute(
                select(User.id, User.username, User.membership_tier)
            )
            users = []
            for row in result:
                users.append({
                    'id': row.id,
                    'username': row.username,
                    'membership_tier': row.membership_tier or 'free'
                })
            return users

    except Exception as e:
        logger.error(f"Error fetching active users: {e}")
        return []


async def calculate_user_stats(user_id: int) -> Dict[str, Any]:
    """
    计算用户统计数据

    Args:
        user_id: 用户ID

    Returns:
        统计数据字典
    """
    stats = {
        'total_articles': 0,
        'total_words': 0,
        'monthly_articles': 0,
        'quota_used': 0,
        'quota_total': 0,
        'avg_score': 0.0,
        'score_history': [],
        'platform_stats': {},
        'hotspot_matches': 0,
        'keyword_hit_rate': 0.0,
        'model_usage': {}
    }

    try:
        from backend.api.db.session import get_async_db_session as get_db_session
        from sqlalchemy import select, func, extract
        from backend.api.db.models.article import Article

        async with get_db_session() as session:
            # 1. 基础统计：总创作数、总字数
            result = await session.execute(
                select(
                    func.count(Article.id).label('total'),
                    func.coalesce(func.sum(Article.word_count), 0).label('total_words')
                ).where(
                    Article.user_id == user_id,
                    Article.status == 'completed'
                )
            )
            row = result.one()
            stats['total_articles'] = row.total or 0
            stats['total_words'] = row.total_words or 0

            # 2. 本月生成数
            now = datetime.utcnow()
            first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            result = await session.execute(
                select(func.count(Article.id)).where(
                    Article.user_id == user_id,
                    Article.status == 'completed',
                    Article.created_at >= first_day_of_month
                )
            )
            stats['monthly_articles'] = result.scalar() or 0

            # 3. 配额使用情况
            try:
                from backend.api.db.models.quota import UserQuota
                result = await session.execute(
                    select(UserQuota).where(UserQuota.user_id == user_id)
                )
                quota = result.scalar_one_or_none()
                if quota:
                    stats['quota_used'] = quota.used_count or 0
                    stats['quota_total'] = quota.total_count or 0
            except ImportError:
                logger.debug("UserQuota model not found, skipping quota stats")

            # 4. 平均评分和评分历史
            try:
                from backend.api.db.models.article import ArticleScore

                # 获取最近30天的评分
                thirty_days_ago = now - timedelta(days=30)
                result = await session.execute(
                    select(
                        func.avg(ArticleScore.total_score).label('avg_score'),
                        func.count(ArticleScore.id).label('score_count')
                    ).join(Article).where(
                        Article.user_id == user_id,
                        ArticleScore.scored_at >= thirty_days_ago
                    )
                )
                row = result.one()
                stats['avg_score'] = round(row.avg_score, 1) if row.avg_score else 0.0

                # 评分历史（按天聚合）
                result = await session.execute(
                    select(
                        func.date_trunc('day', ArticleScore.scored_at).label('date'),
                        func.avg(ArticleScore.total_score).label('avg_score')
                    ).join(Article).where(
                        Article.user_id == user_id,
                        ArticleScore.scored_at >= thirty_days_ago
                    ).group_by(
                        func.date_trunc('day', ArticleScore.scored_at)
                    ).order_by(
                        func.date_trunc('day', ArticleScore.scored_at)
                    )
                )

                score_history = []
                for row in result:
                    date_str = row.date.strftime('%Y-%m-%d') if hasattr(row.date, 'strftime') else str(row.date)[:10]
                    score_history.append({
                        'date': date_str,
                        'score': round(row.avg_score, 1)
                    })
                stats['score_history'] = score_history

            except ImportError:
                logger.debug("ArticleScore model not found, skipping score stats")

            # 5. 平台分布统计
            try:
                from backend.api.db.models.article import ArticlePlatform

                result = await session.execute(
                    select(
                        ArticlePlatform.platform,
                        func.count(ArticlePlatform.id).label('count')
                    ).join(Article).where(
                        Article.user_id == user_id
                    ).group_by(ArticlePlatform.platform)
                )

                platform_stats = {}
                for row in result:
                    platform_stats[row.platform] = row.count
                stats['platform_stats'] = platform_stats

            except ImportError:
                logger.debug("ArticlePlatform model not found, skipping platform stats")

            # 6. 模型使用分布
            result = await session.execute(
                select(
                    Article.model_type,
                    func.count(Article.id).label('count')
                ).where(
                    Article.user_id == user_id,
                    Article.status == 'completed'
                ).group_by(Article.model_type)
            )

            model_usage = {}
            for row in result:
                if row.model_type:
                    model_usage[row.model_type] = row.count
            stats['model_usage'] = model_usage

        return stats

    except Exception as e:
        logger.error(f"Error calculating stats for user {user_id}: {e}")
        return stats


async def refresh_user_stats(user_id: int) -> bool:
    """
    刷新单个用户的统计数据

    Args:
        user_id: 用户ID

    Returns:
        True if success
    """
    try:
        from backend.api.db.models.stats import UserStats
        from backend.api.db.session import get_async_db_session as get_db_session
        from sqlalchemy import select

        # 计算统计数据
        stats_data = await calculate_user_stats(user_id)

        async with get_db_session() as session:
            result = await session.execute(
                select(UserStats).where(UserStats.user_id == user_id)
            )
            stats = result.scalar_one_or_none()

            if stats:
                # 更新现有记录
                stats.total_articles = stats_data['total_articles']
                stats.total_words = stats_data['total_words']
                stats.monthly_articles = stats_data['monthly_articles']
                stats.quota_used = stats_data['quota_used']
                stats.quota_total = stats_data['quota_total']
                stats.avg_score = stats_data['avg_score']
                stats.score_history = stats_data['score_history']
                stats.platform_stats = stats_data['platform_stats']
                stats.model_usage = stats_data['model_usage']
                # hotspot_matches 和 keyword_hit_rate 由 alert_worker 更新
                stats.updated_at = datetime.utcnow()
            else:
                # 创建新记录
                stats = UserStats(
                    user_id=user_id,
                    total_articles=stats_data['total_articles'],
                    total_words=stats_data['total_words'],
                    monthly_articles=stats_data['monthly_articles'],
                    quota_used=stats_data['quota_used'],
                    quota_total=stats_data['quota_total'],
                    avg_score=stats_data['avg_score'],
                    score_history=stats_data['score_history'],
                    platform_stats=stats_data['platform_stats'],
                    model_usage=stats_data['model_usage'],
                    hotspot_matches=0,
                    keyword_hit_rate=0.0,
                    updated_at=datetime.utcnow()
                )
                session.add(stats)

            await session.commit()
            logger.debug(f"Refreshed stats for user {user_id}")
            return True

    except ImportError:
        logger.warning("UserStats model not found, skipping stats refresh")
        return False
    except Exception as e:
        logger.error(f"Error refreshing stats for user {user_id}: {e}")
        return False


async def refresh_all_user_stats(ctx) -> Dict[str, Any]:
    """
    ARQ定时任务：刷新所有用户统计数据

    执行频率: 每小时

    Args:
        ctx: ARQ context

    Returns:
        执行结果统计
    """
    logger.info("=" * 60)
    logger.info("Starting stats refresh task")
    logger.info(f"Time: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    stats = {
        'users_total': 0,
        'users_refreshed': 0,
        'users_failed': 0,
        'errors': []
    }

    try:
        # 获取所有活跃用户
        users = await get_all_active_users()
        stats['users_total'] = len(users)

        logger.info(f"Found {len(users)} users to refresh")

        # 逐个刷新用户统计
        for user in users:
            user_id = user['id']
            try:
                success = await refresh_user_stats(user_id)
                if success:
                    stats['users_refreshed'] += 1
                else:
                    stats['users_failed'] += 1
            except Exception as e:
                stats['users_failed'] += 1
                error_msg = f"Error refreshing user {user_id}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)

        logger.info("=" * 60)
        logger.info("Stats refresh task completed")
        logger.info(f"Stats: {stats}")
        logger.info("=" * 60)

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        logger.exception(f"Fatal error in refresh_all_user_stats: {e}")
        return {
            'success': False,
            'error': str(e),
            'stats': stats
        }


async def increment_user_article_count(user_id: int, word_count: int = 0) -> bool:
    """
    增量更新用户文章计数（文章生成完成后调用）

    Args:
        user_id: 用户ID
        word_count: 文章字数

    Returns:
        True if success
    """
    try:
        from backend.api.db.models.stats import UserStats
        from backend.api.db.session import get_async_db_session as get_db_session
        from sqlalchemy import select

        async with get_db_session() as session:
            result = await session.execute(
                select(UserStats).where(UserStats.user_id == user_id)
            )
            stats = result.scalar_one_or_none()

            if stats:
                stats.total_articles = (stats.total_articles or 0) + 1
                stats.total_words = (stats.total_words or 0) + word_count
                stats.monthly_articles = (stats.monthly_articles or 0) + 1
                stats.updated_at = datetime.utcnow()
            else:
                stats = UserStats(
                    user_id=user_id,
                    total_articles=1,
                    total_words=word_count,
                    monthly_articles=1,
                    updated_at=datetime.utcnow()
                )
                session.add(stats)

            await session.commit()
            logger.debug(f"Incremented article count for user {user_id}")
            return True

    except ImportError:
        logger.warning("UserStats model not found, skipping article count update")
        return False
    except Exception as e:
        logger.error(f"Error incrementing article count for user {user_id}: {e}")
        return False


async def update_user_score_stats(user_id: int, new_score: float) -> bool:
    """
    更新用户评分统计（评分完成后调用）

    Args:
        user_id: 用户ID
        new_score: 新评分

    Returns:
        True if success
    """
    try:
        from backend.api.db.models.stats import UserStats
        from backend.api.db.session import get_async_db_session as get_db_session
        from sqlalchemy import select

        async with get_db_session() as session:
            result = await session.execute(
                select(UserStats).where(UserStats.user_id == user_id)
            )
            stats = result.scalar_one_or_none()

            if stats:
                # 更新平均分
                current_avg = stats.avg_score or 0.0
                current_count = stats.total_articles or 0
                if current_count > 0:
                    new_avg = (current_avg * (current_count - 1) + new_score) / current_count
                    stats.avg_score = round(new_avg, 1)

                # 添加评分历史
                today = datetime.utcnow().strftime('%Y-%m-%d')
                score_history = stats.score_history or []

                # 查找今天的记录
                today_record = None
                for record in score_history:
                    if record.get('date') == today:
                        today_record = record
                        break

                if today_record:
                    # 更新今天的平均分
                    old_count = today_record.get('count', 1)
                    old_avg = today_record.get('score', 0)
                    new_day_avg = (old_avg * old_count + new_score) / (old_count + 1)
                    today_record['score'] = round(new_day_avg, 1)
                    today_record['count'] = old_count + 1
                else:
                    score_history.append({
                        'date': today,
                        'score': round(new_score, 1),
                        'count': 1
                    })

                # 只保留最近30天
                score_history = score_history[-30:]
                stats.score_history = score_history
                stats.updated_at = datetime.utcnow()
            else:
                # 创建新记录
                today = datetime.utcnow().strftime('%Y-%m-%d')
                stats = UserStats(
                    user_id=user_id,
                    avg_score=round(new_score, 1),
                    score_history=[{'date': today, 'score': round(new_score, 1), 'count': 1}],
                    updated_at=datetime.utcnow()
                )
                session.add(stats)

            await session.commit()
            logger.debug(f"Updated score stats for user {user_id}")
            return True

    except ImportError:
        logger.warning("UserStats model not found, skipping score stats update")
        return False
    except Exception as e:
        logger.error(f"Error updating score stats for user {user_id}: {e}")
        return False
