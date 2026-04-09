# -*- coding: utf-8 -*-
"""
Writing Agent Service
写作Agent服务
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update, and_, func
from sqlalchemy.orm import selectinload

from backend.api.db.session import get_async_db_session
from backend.api.db.models.agent import WritingAgent, AgentDraft
from backend.api.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class AgentService:
    """写作Agent服务"""

    async def create_agent(
        self,
        user_id: int,
        name: str,
        trigger_rules: Dict[str, Any],
        platform: str,
        style_id: Optional[str] = None,
        generate_images: bool = False,
        max_daily: int = 5,
        min_hot_score: int = 70
    ) -> WritingAgent:
        """
        创建写作Agent

        Args:
            user_id: 用户ID
            name: Agent名称
            trigger_rules: 触发规则配置
            platform: 默认输出平台
            style_id: 风格ID（可选）
            generate_images: 是否生成图片
            max_daily: 每日最大生成数
            min_hot_score: 最小热度分

        Returns:
            创建的WritingAgent对象
        """
        async with get_async_db_session() as session:
            agent = WritingAgent(
                id=uuid4(),
                user_id=user_id,
                name=name,
                is_active=True,
                trigger_rules=trigger_rules,
                platform=platform,
                style_id=style_id,
                generate_images=generate_images,
                max_daily=max_daily,
                min_hot_score=min_hot_score,
                total_triggered=0,
                today_triggered=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(agent)
            await session.commit()

            logger.info(f"Created writing agent {agent.id} for user {user_id}")
            return agent

    async def update_agent(
        self,
        agent_id: UUID,
        user_id: int,
        **kwargs
    ) -> Optional[WritingAgent]:
        """
        更新Agent配置

        Args:
            agent_id: Agent ID
            user_id: 用户ID（用于权限验证）
            **kwargs: 要更新的字段

        Returns:
            更新后的Agent对象或None
        """
        async with get_async_db_session() as session:
            result = await session.execute(
                select(WritingAgent).where(
                    and_(
                        WritingAgent.id == agent_id,
                        WritingAgent.user_id == user_id
                    )
                )
            )
            agent = result.scalar_one_or_none()

            if not agent:
                return None

            # 更新允许的字段
            allowed_fields = [
                'name', 'is_active', 'trigger_rules', 'platform',
                'style_id', 'generate_images', 'max_daily', 'min_hot_score'
            ]
            for field in allowed_fields:
                if field in kwargs:
                    setattr(agent, field, kwargs[field])

            agent.updated_at = datetime.now(timezone.utc)
            await session.commit()

            logger.info(f"Updated agent {agent_id}")
            return agent

    async def delete_agent(self, agent_id: UUID, user_id: int) -> bool:
        """
        删除Agent

        Args:
            agent_id: Agent ID
            user_id: 用户ID（用于权限验证）

        Returns:
            是否成功删除
        """
        async with get_async_db_session() as session:
            result = await session.execute(
                select(WritingAgent).where(
                    and_(
                        WritingAgent.id == agent_id,
                        WritingAgent.user_id == user_id
                    )
                )
            )
            agent = result.scalar_one_or_none()

            if not agent:
                return False

            await session.delete(agent)
            await session.commit()

            logger.info(f"Deleted agent {agent_id}")
            return True

    async def get_agent(self, agent_id: UUID, user_id: int) -> Optional[WritingAgent]:
        """
        获取Agent详情

        Args:
            agent_id: Agent ID
            user_id: 用户ID（用于权限验证）

        Returns:
            Agent对象或None
        """
        async with get_async_db_session() as session:
            result = await session.execute(
                select(WritingAgent).where(
                    and_(
                        WritingAgent.id == agent_id,
                        WritingAgent.user_id == user_id
                    )
                )
            )
            return result.scalar_one_or_none()

    async def list_user_agents(
        self,
        user_id: int,
        include_inactive: bool = False
    ) -> List[WritingAgent]:
        """
        获取用户的Agent列表

        Args:
            user_id: 用户ID
            include_inactive: 是否包含未启用的Agent

        Returns:
            Agent列表
        """
        async with get_async_db_session() as session:
            query = select(WritingAgent).where(WritingAgent.user_id == user_id)

            if not include_inactive:
                query = query.where(WritingAgent.is_active == True)

            query = query.order_by(WritingAgent.created_at.desc())

            result = await session.execute(query)
            return result.scalars().all()

    async def evaluate_hotspot_for_agent(
        self,
        agent: WritingAgent,
        hotspot: Dict[str, Any]
    ) -> bool:
        """
        评估热点是否匹配Agent规则

        Args:
            agent: Agent对象
            hotspot: 热点数据

        Returns:
            是否匹配
        """
        rules = agent.trigger_rules or {}

        # 检查来源
        allowed_sources = rules.get('sources', [])
        hotspot_source = hotspot.get('source', '')
        if allowed_sources and hotspot_source not in allowed_sources:
            return False

        # 检查关键词匹配
        keywords = rules.get('keywords', [])
        hotspot_title = hotspot.get('title', '') or hotspot.get('word', '')
        if keywords:
            matched = False
            for keyword in keywords:
                if keyword.lower() in hotspot_title.lower():
                    matched = True
                    break
            if not matched:
                return False

        # 检查排除词
        exclude_keywords = rules.get('exclude_keywords', [])
        for exclude in exclude_keywords:
            if exclude.lower() in hotspot_title.lower():
                return False

        # 检查分类
        allowed_categories = rules.get('categories', [])
        hotspot_category = hotspot.get('category', '')
        if allowed_categories and hotspot_category not in allowed_categories:
            return False

        # 检查最小热度值
        min_heat = rules.get('min_heat', 0)
        hotspot_heat = hotspot.get('heat', 0) or hotspot.get('hot_score', 0)
        if min_heat and hotspot_heat < min_heat:
            return False

        return True

    async def generate_draft(
        self,
        agent_id: UUID,
        hotspot: Dict[str, Any]
    ) -> Optional[AgentDraft]:
        """
        为匹配的热点生成草稿

        Args:
            agent_id: Agent ID
            hotspot: 热点数据

        Returns:
            创建的草稿对象或None
        """
        async with get_async_db_session() as session:
            # 获取Agent
            result = await session.execute(
                select(WritingAgent).where(WritingAgent.id == agent_id)
            )
            agent = result.scalar_one_or_none()

            if not agent or not agent.is_active:
                logger.warning(f"Agent {agent_id} not found or inactive")
                return None

            # 检查每日限制
            if agent.today_triggered >= agent.max_daily:
                logger.info(f"Agent {agent_id} reached daily limit")
                return None

            # 检查是否已存在相同热点的草稿
            hotspot_title = hotspot.get('title', '') or hotspot.get('word', '')
            existing_result = await session.execute(
                select(AgentDraft).where(
                    and_(
                        AgentDraft.agent_id == agent_id,
                        AgentDraft.hotspot_title == hotspot_title,
                        AgentDraft.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
                    )
                )
            )
            if existing_result.scalar_one_or_none():
                logger.debug(f"Draft already exists for hotspot: {hotspot_title}")
                return None

            # 创建草稿记录
            draft = AgentDraft(
                id=uuid4(),
                agent_id=agent_id,
                user_id=agent.user_id,
                hotspot_title=hotspot_title,
                hotspot_source=hotspot.get('source', 'unknown'),
                hotspot_url=hotspot.get('url'),
                hotspot_heat=hotspot.get('heat') or hotspot.get('hot_score'),
                status='pending',
                created_at=datetime.now(timezone.utc)
            )
            session.add(draft)

            # 更新Agent统计
            agent.total_triggered += 1
            agent.today_triggered += 1
            agent.last_triggered_at = datetime.now(timezone.utc)

            await session.commit()

            # 提交ARQ任务生成文章
            try:
                from arq import create_pool
                from backend.api.workers.worker_settings import redis_settings

                redis = await create_pool(redis_settings)
                await redis.enqueue_job(
                    'generate_draft_for_hotspot',
                    str(draft.id),
                    str(agent_id),
                    hotspot
                )
                await redis.close()

                logger.info(f"Created draft {draft.id} for agent {agent_id}")
            except Exception as e:
                logger.error(f"Failed to enqueue draft generation: {e}")

            return draft

    async def get_drafts_for_review(
        self,
        user_id: int,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取待审核的草稿列表

        Args:
            user_id: 用户ID
            status: 状态筛选（可选）
            page: 页码
            limit: 每页数量

        Returns:
            草稿列表和分页信息
        """
        async with get_async_db_session() as session:
            # 构建查询
            query = select(AgentDraft).where(AgentDraft.user_id == user_id)

            if status:
                query = query.where(AgentDraft.status == status)

            # 获取总数
            count_result = await session.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = count_result.scalar()

            # 分页
            query = query.order_by(AgentDraft.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)

            result = await session.execute(query)
            drafts = result.scalars().all()

            # 获取Agent名称映射
            agent_ids = [draft.agent_id for draft in drafts]
            agent_names = {}
            if agent_ids:
                agent_result = await session.execute(
                    select(WritingAgent.id, WritingAgent.name)
                    .where(WritingAgent.id.in_(agent_ids))
                )
                agent_names = {str(row[0]): row[1] for row in agent_result.all()}

            return {
                'items': [
                    {
                        'id': str(draft.id),
                        'agent_id': str(draft.agent_id),
                        'agent_name': agent_names.get(str(draft.agent_id), 'Unknown'),
                        'hotspot_title': draft.hotspot_title,
                        'hotspot_source': draft.hotspot_source,
                        'hotspot_heat': draft.hotspot_heat,
                        'status': draft.status,
                        'article_id': str(draft.article_id) if draft.article_id else None,
                        'user_rating': draft.user_rating,
                        'user_notes': draft.user_notes,
                        'created_at': draft.created_at.isoformat() if draft.created_at else None,
                        'reviewed_at': draft.reviewed_at.isoformat() if draft.reviewed_at else None,
                    }
                    for draft in drafts
                ],
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }

    async def review_draft(
        self,
        draft_id: UUID,
        user_id: int,
        action: str,  # 'accept' or 'discard'
        rating: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[AgentDraft]:
        """
        审核草稿

        Args:
            draft_id: 草稿ID
            user_id: 用户ID（权限验证）
            action: 操作（accept/discard）
            rating: 评分（1-5，可选）
            notes: 备注（可选）

        Returns:
            更新后的草稿对象或None
        """
        async with get_async_db_session() as session:
            result = await session.execute(
                select(AgentDraft).where(
                    and_(
                        AgentDraft.id == draft_id,
                        AgentDraft.user_id == user_id
                    )
                )
            )
            draft = result.scalar_one_or_none()

            if not draft:
                return None

            if action == 'accept':
                draft.status = 'reviewed'
            elif action == 'discard':
                draft.status = 'discarded'
            else:
                return None

            if rating is not None:
                draft.user_rating = max(1, min(5, rating))

            if notes:
                draft.user_notes = notes

            draft.reviewed_at = datetime.now(timezone.utc)
            await session.commit()

            logger.info(f"Reviewed draft {draft_id}: {action}")
            return draft

    async def reset_daily_counters(self) -> int:
        """
        重置所有Agent的每日计数器
        应在每天凌晨0点执行

        Returns:
            更新的Agent数量
        """
        async with get_async_db_session() as session:
            result = await session.execute(
                update(WritingAgent)
                .values(today_triggered=0)
            )
            await session.commit()

            logger.info(f"Reset daily counters for {result.rowcount} agents")
            return result.rowcount


# 全局实例
agent_service = AgentService()
