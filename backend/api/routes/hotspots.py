# -*- coding: utf-8 -*-
"""热点路由 - 增强版"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from backend.api.services.hotspots_service import hotspots_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_hotspots(source: Optional[str] = "baidu"):
    """获取热点数据（带 Redis 缓存）"""
    supported_sources = ['baidu', 'weibo', 'douyin', 'thepaper', '36kr']
    
    if source not in supported_sources:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的热点源，支持的源: {', '.join(supported_sources)}"
        )
    
    result = await hotspots_service.get_hotspots(source)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=500,
            detail=result.get('error', '获取热点数据失败')
        )
    
    return {
        "source": source,
        "data": result['data'],
        "from_cache": result.get('from_cache', False),
        "count": len(result['data'])
    }


@router.get("/sources")
async def get_hotspot_sources():
    """获取支持的热点源列表"""
    return {
        "sources": [
            {"id": "baidu", "name": "百度热搜", "icon": "🔥"},
            {"id": "weibo", "name": "微博热搜", "icon": "📱"},
            {"id": "douyin", "name": "抖音热搜", "icon": "🎵"},
            {"id": "thepaper", "name": "澎湃新闻", "icon": "📰"},
            {"id": "36kr", "name": "36氪", "icon": "💼"}
        ]
    }
