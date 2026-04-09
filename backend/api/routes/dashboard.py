"""Dashboard API routes for user statistics."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.core.dependencies import get_current_user, get_db as get_db_session
from backend.api.services.analytics_service import AnalyticsService
from backend.api.services.tier_service import TierService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ============ Pydantic Models ============

class DashboardResponse(BaseModel):
    # Free tier fields
    total_articles: int = Field(..., description="总创作数")
    total_words: int = Field(..., description="累计字数")
    monthly_articles: int = Field(..., description="本月生成数")
    quota_used: int = Field(..., description="已用配额")
    quota_total: int = Field(..., description="总配额")

    # Pro tier fields (optional)
    avg_score: Optional[float] = Field(None, description="平均评分")
    score_history: Optional[list] = Field(None, description="评分趋势")
    platform_stats: Optional[dict] = Field(None, description="平台分布")

    # Ultra tier fields (optional)
    hotspot_matches: Optional[int] = Field(None, description="热点匹配数")
    keyword_hit_rate: Optional[float] = Field(None, description="关键词命中率")
    model_usage: Optional[dict] = Field(None, description="模型使用分布")


# ============ Dashboard Routes ============

@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """
    Get dashboard statistics for current user.

    Returns different data based on membership tier:
    - Free: Basic stats (articles, words, quota)
    - Pro: + Score history, platform distribution
    - Ultra: + Hotspot matches, keyword hit rate, model usage
    """
    # Get user's tier
    tier = TierService.get_user_tier(current_user_id)

    # Get stats
    analytics_service = AnalyticsService(session)
    stats = await analytics_service.get_user_stats(current_user_id, tier)

    return DashboardResponse(**stats)
