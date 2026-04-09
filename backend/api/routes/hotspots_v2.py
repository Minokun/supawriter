# -*- coding: utf-8 -*-
"""热点路由 V2 - 基于 newsnow API 的增强版"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.db.session import get_db
from backend.api.services.hotspots_v2_service import HotspotsV2Service
from backend.api.core.dependencies import require_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ Response Models ============

from pydantic import BaseModel, Field


class HotspotSourceResponse(BaseModel):
    """平台配置响应"""
    id: str
    name: str
    icon: Optional[str] = None
    category: Optional[str] = None
    enabled: bool = True


class HotspotItemResponse(BaseModel):
    """热点条目响应"""
    id: int
    title: str
    url: Optional[str] = None
    source: str
    rank: int
    rank_prev: Optional[int] = None
    rank_change: int = 0
    hot_value: Optional[int] = None
    is_new: bool = False
    description: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class HotspotListResponse(BaseModel):
    """热点列表响应"""
    source: str
    updated_at: datetime
    items: List[HotspotItemResponse]
    count: int


class SyncResultResponse(BaseModel):
    """同步结果响应"""
    source: str
    success: bool
    created: int = 0
    updated: int = 0
    total: int = 0
    error: Optional[str] = None


class RankHistoryResponse(BaseModel):
    """排名历史响应"""
    hotspot_id: int
    source: str
    history: List[Dict[str, Any]]


# ============ API Endpoints ============

@router.get("/sources", response_model=Dict[str, List[HotspotSourceResponse]])
async def get_sources(
    session: AsyncSession = Depends(get_db)
):
    """
    获取支持的平台列表

    Returns:
        所有启用平台的配置信息
    """
    service = HotspotsV2Service(session)
    sources = await service.get_sources()

    return {
        "sources": [
            HotspotSourceResponse(**s) for s in sources
        ]
    }


@router.get("/latest", response_model=Dict[str, Any])
async def get_all_latest(
    limit: int = Query(default=10, ge=1, le=50, description="每个平台返回的条目数"),
    session: AsyncSession = Depends(get_db)
):
    """
    获取所有平台的最新热点

    Args:
        limit: 每个平台返回的最大条目数

    Returns:
        各平台热点数据
    """
    service = HotspotsV2Service(session)
    data = await service.get_all_latest(limit)

    result = {}
    for source, items in data.items():
        result[source] = {
            "updated_at": datetime.utcnow(),
            "items": [HotspotItemResponse.model_validate(item) for item in items],
            "count": len(items)
        }

    return result


@router.get("/latest/{source}", response_model=HotspotListResponse)
async def get_latest_by_source(
    source: str,
    limit: int = Query(default=50, ge=1, le=100, description="返回条目数"),
    session: AsyncSession = Depends(get_db)
):
    """
    获取指定平台的最新热点

    Args:
        source: 平台 ID (baidu, weibo, douyin, etc.)
        limit: 返回的最大条目数

    Returns:
        该平台的热点列表
    """
    service = HotspotsV2Service(session)
    items = await service.get_latest_by_source(source, limit)

    if not items:
        # 如果没有数据，尝试同步
        logger.info(f"{source} 无缓存数据，尝试同步")
        result = await service.sync_source(source)
        if result.success:
            items = await service.get_latest_by_source(source, limit)

    return HotspotListResponse(
        source=source,
        updated_at=datetime.utcnow(),
        items=[HotspotItemResponse.model_validate(item) for item in items],
        count=len(items)
    )


@router.get("/history/{source}")
async def get_source_history(
    source: str,
    hours: int = Query(default=24, ge=1, le=168, description="历史时间范围（小时）"),
    limit: int = Query(default=100, ge=1, le=500, description="返回条目数"),
    session: AsyncSession = Depends(get_db)
):
    """
    获取指定平台的历史热点记录

    Args:
        source: 平台 ID
        hours: 历史时间范围（小时）
        limit: 返回的最大条目数

    Returns:
        历史热点记录
    """
    from backend.api.repositories.hotspot import HotspotRankHistoryRepository

    history_repo = HotspotRankHistoryRepository(session)
    history = await history_repo.get_source_history(source, hours, limit)

    return {
        "source": source,
        "hours": hours,
        "records": [
            {
                "id": h.id,
                "hotspot_item_id": h.hotspot_item_id,
                "rank": h.rank,
                "hot_value": h.hot_value,
                "is_new": h.is_new,
                "recorded_at": h.recorded_at.isoformat()
            }
            for h in history
        ],
        "count": len(history)
    }


@router.get("/trend/{hotspot_id}", response_model=RankHistoryResponse)
async def get_trend(
    hotspot_id: int,
    hours: int = Query(default=24, ge=1, le=168, description="历史时间范围（小时）"),
    session: AsyncSession = Depends(get_db)
):
    """
    获取热点排名趋势

    Args:
        hotspot_id: 热点 ID
        hours: 历史时间范围（小时）

    Returns:
        排名历史数据
    """
    from backend.api.db.models.hotspot import HotspotItem

    service = HotspotsV2Service(session)

    # 获取热点信息
    item = await service.item_repo.get_by_id(hotspot_id)
    if not item:
        raise HTTPException(status_code=404, detail="热点不存在")

    history = await service.get_rank_history(hotspot_id, hours)

    return RankHistoryResponse(
        hotspot_id=hotspot_id,
        source=item.source,
        history=history
    )


@router.post("/sync", response_model=Dict[str, Any])
async def sync_hotspots(
    source: Optional[str] = Query(default=None, description="指定同步的平台，不指定则同步全部"),
    session: AsyncSession = Depends(get_db),
    _admin_user_id: int = Depends(require_admin)
):
    """
    手动同步热点数据

    Args:
        source: 指定同步的平台 ID，不指定则同步全部启用平台

    Returns:
        同步结果

    Note:
        此接口需要超级管理员权限
    """
    service = HotspotsV2Service(session)

    if source:
        # 同步单个平台
        result = await service.sync_source(source)
        return {
            "success": result.success,
            "results": {source: SyncResultResponse(
                source=result.source,
                success=result.success,
                created=result.created,
                updated=result.updated,
                total=result.total,
                error=result.error
            ).model_dump()}
        }
    else:
        # 同步所有平台
        results = await service.sync_all_sources()
        return {
            "success": all(r.success for r in results.values()),
            "results": {
                sid: SyncResultResponse(
                    source=r.source,
                    success=r.success,
                    created=r.created,
                    updated=r.updated,
                    total=r.total,
                    error=r.error
                ).model_dump()
                for sid, r in results.items()
            }
        }


@router.post("/init")
async def init_sources(
    session: AsyncSession = Depends(get_db)
):
    """
    初始化平台配置

    从默认配置创建平台数据

    Returns:
        创建的平台数量
    """
    service = HotspotsV2Service(session)
    created = await service.init_sources()

    return {
        "success": True,
        "created": created,
        "message": f"初始化了 {created} 个平台配置"
    }


@router.delete("/cache")
async def clear_cache(
    source: Optional[str] = Query(default=None, description="指定清除的平台缓存，不指定则清除全部"),
    session: AsyncSession = Depends(get_db),
    _admin_user_id: int = Depends(require_admin),
):
    """
    清除热点缓存

    Args:
        source: 指定清除的平台，不指定则清除全部

    Returns:
        操作结果
    """
    service = HotspotsV2Service(session)
    await service.clear_cache(source)

    return {
        "success": True,
        "message": f"已清除 {source or '全部'} 热点缓存"
    }
