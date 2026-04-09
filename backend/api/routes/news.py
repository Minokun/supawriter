# -*- coding: utf-8 -*-
"""
SupaWriter 新闻 API 路由
处理新闻资讯数据获取
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
import logging

from backend.api.core.dependencies import get_current_user_optional


logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


@router.get("/")
async def get_news(
    source: Optional[str] = Query(None, description="新闻来源"),
    category: Optional[str] = Query(None, description="新闻分类"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_user_id: Optional[int] = Depends(get_current_user_optional)
):
    """
    获取新闻资讯数据

    Args:
        source: 新闻来源筛选
        category: 分类筛选
        limit: 返回数量
        current_user_id: 当前用户 ID（可选）

    Returns:
        新闻数据列表
    """
    # 复用 page/news.py 的逻辑
    from page.news import get_all_news

    try:
        # 获取新闻数据
        news_data = get_all_news()

        # 筛选来源
        if source:
            news_data = [n for n in news_data if n.get('source') == source]

        # 筛选分类
        if category:
            news_data = [n for n in news_data if n.get('category') == category]

        # 限制数量
        news_data = news_data[:limit]

        return {
            "items": news_data,
            "total": len(news_data),
            "source": source,
            "category": category
        }

    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return {
            "items": [],
            "total": 0,
            "error": str(e)
        }


@router.get("/sources")
async def get_news_sources(
    current_user_id: Optional[int] = Depends(get_current_user_optional)
):
    """
    获取可用的新闻来源列表

    Args:
        current_user_id: 当前用户 ID（可选）

    Returns:
        新闻来源列表
    """
    sources = [
        {
            "id": "tech",
            "name": "科技新闻",
            "description": "最新科技资讯",
            "icon": "💻"
        },
        {
            "id": "finance",
            "name": "财经新闻",
            "description": "财经商业资讯",
            "icon": "📈"
        },
        {
            "id": "ai",
            "name": "AI 资讯",
            "description": "人工智能新闻",
            "icon": "🤖"
        }
    ]

    return {"sources": sources}


@router.get("/categories")
async def get_news_categories(
    current_user_id: Optional[int] = Depends(get_current_user_optional)
):
    """
    获取新闻分类列表

    Args:
        current_user_id: 当前用户 ID（可选）

    Returns:
        分类列表
    """
    categories = [
        {"id": "tech", "name": "科技"},
        {"id": "finance", "name": "财经"},
        {"id": "ai", "name": "AI"},
        {"id": "startup", "name": "创业"},
        {"id": "product", "name": "产品"}
    ]

    return {"categories": categories}
