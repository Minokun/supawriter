# -*- coding: utf-8 -*-
"""
Pricing API Routes
定价API路由
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Dict, Any, List

from backend.api.services.pricing_service import PricingService

router = APIRouter(prefix="/pricing", tags=["pricing"])


# ============ Pydantic Models ============

class PricingPlansResponse(BaseModel):
    """定价方案响应"""
    plans: List[Dict[str, Any]]
    period: str


class QuotaPacksResponse(BaseModel):
    """额度包响应"""
    quota_packs: List[Dict[str, Any]]


# ============ Pricing Routes ============

@router.get("/plans", response_model=PricingPlansResponse)
async def get_pricing_plans(
    period: str = Query("monthly", description="Billing period: monthly, quarterly, yearly")
):
    """
    获取定价方案

    - period: 计费周期 (monthly, quarterly, yearly)
    - 返回所有方案的定价信息
    """
    if period not in ["monthly", "quarterly", "yearly"]:
        period = "monthly"

    plans = PricingService.get_pricing_plans(period)

    return {
        "plans": plans,
        "period": period
    }


@router.get("/quota-packs", response_model=QuotaPacksResponse)
async def get_quota_packs():
    """
    获取额度包配置

    - 返回所有可购买的额度包信息
    """
    quota_packs = PricingService.get_quota_packs()

    return {
        "quota_packs": quota_packs
    }
