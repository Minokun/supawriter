# -*- coding: utf-8 -*-
"""
Writing Agent API Routes
写作Agent API路由
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.api.core.dependencies import get_current_user
from backend.api.services.agent_service import agent_service
from backend.api.services.tier_service import TierService

router = APIRouter(prefix="/agents", tags=["agents"])


# ============ Pydantic Models ============

class TriggerRules(BaseModel):
    """触发规则配置"""
    sources: List[str] = Field(default_factory=list, description="监控的热点源")
    keywords: Optional[List[str]] = Field(None, description="关键词匹配")
    categories: Optional[List[str]] = Field(None, description="分类筛选")
    exclude_keywords: Optional[List[str]] = Field(None, description="排除词")
    min_heat: Optional[int] = Field(None, description="最小热度值")


class CreateAgentRequest(BaseModel):
    """创建Agent请求"""
    name: str = Field(..., min_length=1, max_length=100, description="Agent名称")
    trigger_rules: TriggerRules = Field(..., description="触发规则")
    platform: str = Field(..., description="默认输出平台")
    style_id: Optional[str] = Field(None, description="风格ID")
    generate_images: bool = Field(False, description="是否生成图片")
    max_daily: int = Field(5, ge=1, le=50, description="每日最大生成数")
    min_hot_score: int = Field(70, ge=0, le=100, description="最小热度分")


class UpdateAgentRequest(BaseModel):
    """更新Agent请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    trigger_rules: Optional[TriggerRules] = None
    platform: Optional[str] = None
    style_id: Optional[str] = None
    generate_images: Optional[bool] = None
    max_daily: Optional[int] = Field(None, ge=1, le=50)
    min_hot_score: Optional[int] = Field(None, ge=0, le=100)


class AgentResponse(BaseModel):
    """Agent响应"""
    id: str
    name: str
    is_active: bool
    trigger_rules: dict
    platform: str
    style_id: Optional[str] = None
    generate_images: bool
    max_daily: int
    min_hot_score: int
    total_triggered: int
    today_triggered: int
    last_triggered_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AgentListResponse(BaseModel):
    """Agent列表响应"""
    agents: List[AgentResponse]


class DraftResponse(BaseModel):
    """草稿响应"""
    id: str
    agent_id: str
    agent_name: str
    hotspot_title: str
    hotspot_source: str
    hotspot_heat: Optional[int] = None
    status: str
    article_id: Optional[str] = None
    user_rating: Optional[int] = None
    user_notes: Optional[str] = None
    created_at: Optional[str] = None
    reviewed_at: Optional[str] = None


class DraftListResponse(BaseModel):
    """草稿列表响应"""
    items: List[DraftResponse]
    total: int
    page: int
    limit: int
    pages: int


class ReviewDraftRequest(BaseModel):
    """审核草稿请求"""
    action: str = Field(..., description="操作: accept/discard")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分1-5")
    notes: Optional[str] = Field(None, max_length=1000, description="备注")


class ReviewDraftResponse(BaseModel):
    """审核草稿响应"""
    message: str
    draft_id: str
    status: str


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


# ============ Helper Functions ============

def check_agent_limit(user_id: int):
    """检查Agent数量限制"""
    tier = TierService.get_user_tier(user_id)

    # 各等级的Agent数量限制
    agent_limits = {"free": 0, "pro": 2, "ultra": 10, "superuser": 10}
    limit = agent_limits.get(tier, 0)

    if limit == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Writing Agent feature is not available on your plan. Upgrade to Pro or Ultra."
        )

    return limit


# ============ Agent Routes ============

@router.post("", response_model=AgentResponse)
async def create_agent(
    request: CreateAgentRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    创建写作Agent

    - Free用户无法创建Agent
    - Pro用户最多2个
    - Ultra用户最多10个
    """
    # 检查Agent数量限制
    limit = check_agent_limit(current_user_id)

    # 获取当前Agent数量
    agents = await agent_service.list_user_agents(current_user_id)
    if len(agents) >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your plan allows maximum {limit} agents. Delete existing agents to create new ones."
        )

    # 创建Agent
    agent = await agent_service.create_agent(
        user_id=current_user_id,
        name=request.name,
        trigger_rules=request.trigger_rules.dict(),
        platform=request.platform,
        style_id=request.style_id,
        generate_images=request.generate_images,
        max_daily=request.max_daily,
        min_hot_score=request.min_hot_score
    )

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        is_active=agent.is_active,
        trigger_rules=agent.trigger_rules,
        platform=agent.platform,
        style_id=agent.style_id,
        generate_images=agent.generate_images,
        max_daily=agent.max_daily,
        min_hot_score=agent.min_hot_score,
        total_triggered=agent.total_triggered,
        today_triggered=agent.today_triggered,
        last_triggered_at=agent.last_triggered_at.isoformat() if agent.last_triggered_at else None,
        created_at=agent.created_at.isoformat() if agent.created_at else None,
        updated_at=agent.updated_at.isoformat() if agent.updated_at else None
    )


@router.get("", response_model=AgentListResponse)
async def list_agents(
    include_inactive: bool = False,
    current_user_id: int = Depends(get_current_user)
):
    """获取用户的Agent列表"""
    agents = await agent_service.list_user_agents(
        user_id=current_user_id,
        include_inactive=include_inactive
    )

    return AgentListResponse(
        agents=[
            AgentResponse(
                id=str(agent.id),
                name=agent.name,
                is_active=agent.is_active,
                trigger_rules=agent.trigger_rules,
                platform=agent.platform,
                style_id=agent.style_id,
                generate_images=agent.generate_images,
                max_daily=agent.max_daily,
                min_hot_score=agent.min_hot_score,
                total_triggered=agent.total_triggered,
                today_triggered=agent.today_triggered,
                last_triggered_at=agent.last_triggered_at.isoformat() if agent.last_triggered_at else None,
                created_at=agent.created_at.isoformat() if agent.created_at else None,
                updated_at=agent.updated_at.isoformat() if agent.updated_at else None
            )
            for agent in agents
        ]
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user_id: int = Depends(get_current_user)
):
    """获取Agent详情"""
    agent = await agent_service.get_agent(agent_id, current_user_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        is_active=agent.is_active,
        trigger_rules=agent.trigger_rules,
        platform=agent.platform,
        style_id=agent.style_id,
        generate_images=agent.generate_images,
        max_daily=agent.max_daily,
        min_hot_score=agent.min_hot_score,
        total_triggered=agent.total_triggered,
        today_triggered=agent.today_triggered,
        last_triggered_at=agent.last_triggered_at.isoformat() if agent.last_triggered_at else None,
        created_at=agent.created_at.isoformat() if agent.created_at else None,
        updated_at=agent.updated_at.isoformat() if agent.updated_at else None
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    request: UpdateAgentRequest,
    current_user_id: int = Depends(get_current_user)
):
    """更新Agent配置"""
    # 构建更新数据
    update_data = {}
    for field in ['name', 'is_active', 'platform', 'style_id', 'generate_images', 'max_daily', 'min_hot_score']:
        value = getattr(request, field)
        if value is not None:
            update_data[field] = value

    if request.trigger_rules is not None:
        update_data['trigger_rules'] = request.trigger_rules.dict()

    # 更新Agent
    agent = await agent_service.update_agent(
        agent_id=agent_id,
        user_id=current_user_id,
        **update_data
    )

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        is_active=agent.is_active,
        trigger_rules=agent.trigger_rules,
        platform=agent.platform,
        style_id=agent.style_id,
        generate_images=agent.generate_images,
        max_daily=agent.max_daily,
        min_hot_score=agent.min_hot_score,
        total_triggered=agent.total_triggered,
        today_triggered=agent.today_triggered,
        last_triggered_at=agent.last_triggered_at.isoformat() if agent.last_triggered_at else None,
        created_at=agent.created_at.isoformat() if agent.created_at else None,
        updated_at=agent.updated_at.isoformat() if agent.updated_at else None
    )


@router.delete("/{agent_id}", response_model=MessageResponse)
async def delete_agent(
    agent_id: UUID,
    current_user_id: int = Depends(get_current_user)
):
    """删除Agent"""
    success = await agent_service.delete_agent(agent_id, current_user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")

    return MessageResponse(message="Agent deleted successfully")


# ============ Draft Routes ============

@router.get("/drafts", response_model=DraftListResponse)
async def list_drafts(
    status: Optional[str] = Query(None, description="状态筛选: pending/generating/completed/reviewed/discarded"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user_id: int = Depends(get_current_user)
):
    """获取Agent生成的草稿列表"""
    result = await agent_service.get_drafts_for_review(
        user_id=current_user_id,
        status=status,
        page=page,
        limit=limit
    )

    return DraftListResponse(**result)


@router.put("/drafts/{draft_id}/review", response_model=ReviewDraftResponse)
async def review_draft(
    draft_id: UUID,
    request: ReviewDraftRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    审核草稿

    - action: accept (接受) / discard (丢弃)
    - rating: 1-5星评分（可选）
    - notes: 备注（可选）
    """
    if request.action not in ['accept', 'discard']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'accept' or 'discard'"
        )

    draft = await agent_service.review_draft(
        draft_id=draft_id,
        user_id=current_user_id,
        action=request.action,
        rating=request.rating,
        notes=request.notes
    )

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    return ReviewDraftResponse(
        message=f"Draft {request.action}ed successfully",
        draft_id=str(draft.id),
        status=draft.status
    )


@router.post("/drafts/{draft_id}/publish", response_model=MessageResponse)
async def publish_draft(
    draft_id: UUID,
    current_user_id: int = Depends(get_current_user)
):
    """
    发布草稿（将文章状态改为已完成）

    - 只有已接受的草稿才能发布
    - 发布后会消耗用户的文章配额
    """
    from backend.api.db.session import get_async_db_session
    from backend.api.db.models.agent import AgentDraft
    from sqlalchemy import select

    async with get_async_db_session() as session:
        result = await session.execute(
            select(AgentDraft).where(AgentDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()

        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        if draft.user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        if draft.status != 'reviewed':
            raise HTTPException(
                status_code=400,
                detail="Draft must be reviewed and accepted before publishing"
            )

        if not draft.article_id:
            raise HTTPException(status_code=400, detail="No article associated with this draft")

        # 更新文章状态为completed
        from backend.api.db.models.article import Article
        article_result = await session.execute(
            select(Article).where(Article.id == draft.article_id)
        )
        article = article_result.scalar_one_or_none()

        if article:
            article.status = 'completed'
            await session.commit()

    return MessageResponse(message="Draft published successfully")
