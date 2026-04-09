# -*- coding: utf-8 -*-
"""
Agent Worker - 写作Agent定时任务
每30分钟执行一次，扫描热点并触发Agent生成草稿
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_

from backend.api.db.session import get_async_db_session
from backend.api.db.models.agent import WritingAgent, AgentDraft
from backend.api.services.agent_service import agent_service
from backend.api.services.hotspots_service import hotspots_service

logger = logging.getLogger(__name__)

# 热点源列表
HOTSPOT_SOURCES = ['baidu', 'weibo', 'douyin', 'thepaper', '36kr']


async def get_active_agents() -> List[WritingAgent]:
    """
    获取所有启用的Agent

    Returns:
        Agent列表
    """
    try:
        async with get_async_db_session() as session:
            result = await session.execute(
                select(WritingAgent)
                .where(WritingAgent.is_active == True)
            )
            return result.scalars().all()
    except Exception as e:
        logger.error(f"Error fetching active agents: {e}")
        return []


async def get_all_hotspots() -> List[Dict[str, Any]]:
    """
    获取所有平台的热点数据

    Returns:
        合并后的热点列表
    """
    all_hotspots = []

    for source in HOTSPOT_SOURCES:
        try:
            result = await hotspots_service.get_hotspots(source)
            if result.get('success'):
                hotspots = result.get('data', [])
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


async def scan_hotspots_for_agents(ctx) -> Dict[str, Any]:
    """
    ARQ定时任务：扫描热点并触发Agent

    执行频率: 每30分钟（与alert_worker同时执行）

    流程:
    1. 获取所有启用的Agent
    2. 获取热点数据
    3. 对每个Agent，筛选匹配的热点
    4. 检查每日生成限制
    5. 为匹配的热点生成草稿
    6. 发送通知（可选）

    Args:
        ctx: ARQ context

    Returns:
        执行结果统计
    """
    logger.info("=" * 60)
    logger.info("Starting Agent hotspot scan task")
    logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    stats = {
        'agents_checked': 0,
        'hotspots_checked': 0,
        'drafts_created': 0,
        'errors': []
    }

    try:
        # 1. 获取所有启用的Agent
        agents = await get_active_agents()
        if not agents:
            logger.info("No active agents found, task completed")
            return {'success': True, 'stats': stats}

        stats['agents_checked'] = len(agents)
        logger.info(f"Found {len(agents)} active agents")

        # 2. 获取热点数据
        hotspots = await get_all_hotspots()
        if not hotspots:
            logger.warning("No hotspots fetched, task completed")
            return {'success': True, 'stats': stats}

        stats['hotspots_checked'] = len(hotspots)

        # 3. 对每个Agent进行匹配
        for agent in agents:
            try:
                # 检查每日限制
                if agent.today_triggered >= agent.max_daily:
                    logger.info(f"Agent {agent.id} reached daily limit ({agent.max_daily})")
                    continue

                # 匹配热点
                matched_hotspots = []
                for hotspot in hotspots:
                    if await agent_service.evaluate_hotspot_for_agent(agent, hotspot):
                        matched_hotspots.append(hotspot)

                if not matched_hotspots:
                    logger.debug(f"No matching hotspots for agent {agent.id}")
                    continue

                logger.info(f"Agent {agent.id} matched {len(matched_hotspots)} hotspots")

                # 为匹配的热点生成草稿（受每日限制）
                remaining_quota = agent.max_daily - agent.today_triggered
                for hotspot in matched_hotspots[:remaining_quota]:
                    try:
                        draft = await agent_service.generate_draft(
                            agent_id=agent.id,
                            hotspot=hotspot
                        )
                        if draft:
                            stats['drafts_created'] += 1
                            logger.info(f"Created draft {draft.id} for agent {agent.id}")
                    except Exception as e:
                        error_msg = f"Error generating draft for agent {agent.id}: {e}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)

            except Exception as e:
                error_msg = f"Error processing agent {agent.id}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                continue

        logger.info("=" * 60)
        logger.info("Agent hotspot scan task completed")
        logger.info(f"Stats: {stats}")
        logger.info("=" * 60)

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        logger.exception(f"Fatal error in scan_hotspots_for_agents: {e}")
        return {
            'success': False,
            'error': str(e),
            'stats': stats
        }


async def generate_draft_for_hotspot(
    ctx,
    draft_id: str,
    agent_id: str,
    hotspot: Dict[str, Any]
) -> Dict[str, Any]:
    """
    为特定热点生成草稿

    Args:
        ctx: ARQ context
        draft_id: 草稿ID
        agent_id: Agent ID
        hotspot: 热点数据

    Returns:
        生成结果
    """
    draft_uuid = UUID(draft_id)
    agent_uuid = UUID(agent_id)

    logger.info(f"Generating draft {draft_id} for agent {agent_id}")

    try:
        # 获取Agent配置
        async with get_async_db_session() as session:
            result = await session.execute(
                select(WritingAgent).where(WritingAgent.id == agent_uuid)
            )
            agent = result.scalar_one_or_none()

            if not agent:
                return {'success': False, 'error': 'Agent not found'}

            # 更新草稿状态为generating
            draft_result = await session.execute(
                select(AgentDraft).where(AgentDraft.id == draft_uuid)
            )
            draft = draft_result.scalar_one_or_none()

            if not draft:
                return {'success': False, 'error': 'Draft not found'}

            draft.status = 'generating'
            await session.commit()

        # 调用article_worker生成文章
        from backend.api.workers.article_worker import generate_article_task
        from backend.api.utils.searxng_compat import set_user_context

        # 设置用户上下文
        set_user_context(agent.user_id)

        # 生成文章
        article_result = await generate_article_task(
            None,  # ctx
            task_id=draft_id,  # 使用draft_id作为task_id
            topic=hotspot.get('title', '') or hotspot.get('word', ''),
            user_id=agent.user_id,
            custom_style="",  # 可以从agent.style_id加载
            spider_num=None,
            extra_urls=None,
            model_type="deepseek",
            model_name="deepseek-chat"
        )

        # 更新草稿状态
        async with get_async_db_session() as session:
            draft_result = await session.execute(
                select(AgentDraft).where(AgentDraft.id == draft_uuid)
            )
            draft = draft_result.scalar_one_or_none()

            if article_result.get('success'):
                draft.status = 'completed'
                draft.article_id = UUID(article_result['article_id']) if article_result.get('article_id') else None
                logger.info(f"Draft {draft_id} completed successfully")
            else:
                draft.status = 'failed'
                logger.error(f"Draft {draft_id} failed: {article_result.get('error')}")

            await session.commit()

        # 发送通知（可选）
        try:
            from backend.api.core.redis_client import redis_client
            await redis_client.publish_notification(
                agent.user_id,
                {
                    'type': 'agent_draft_completed',
                    'draft_id': draft_id,
                    'agent_name': agent.name,
                    'hotspot_title': hotspot.get('title', '') or hotspot.get('word', ''),
                    'status': 'completed' if article_result.get('success') else 'failed'
                }
            )
        except Exception as notify_error:
            logger.warning(f"Failed to send notification: {notify_error}")

        return article_result

    except Exception as e:
        logger.exception(f"Error generating draft {draft_id}: {e}")

        # 更新草稿状态为failed
        try:
            async with get_async_db_session() as session:
                draft_result = await session.execute(
                    select(AgentDraft).where(AgentDraft.id == draft_uuid)
                )
                draft = draft_result.scalar_one_or_none()
                if draft:
                    draft.status = 'failed'
                    await session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update draft status: {db_error}")

        return {'success': False, 'error': str(e)}


async def reset_agent_daily_counters(ctx) -> Dict[str, Any]:
    """
    ARQ定时任务：重置Agent每日计数器

    执行频率: 每天凌晨0点

    Args:
        ctx: ARQ context

    Returns:
        执行结果
    """
    logger.info("Resetting agent daily counters...")

    try:
        count = await agent_service.reset_daily_counters()
        logger.info(f"Reset daily counters for {count} agents")
        return {
            'success': True,
            'agents_reset': count
        }
    except Exception as e:
        logger.error(f"Error resetting daily counters: {e}")
        return {
            'success': False,
            'error': str(e)
        }
