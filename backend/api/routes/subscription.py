# -*- coding: utf-8 -*-
"""
Subscription API Routes
订阅和配额API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from backend.api.core.dependencies import get_current_user
from backend.api.db.session import get_async_db_session

router = APIRouter(prefix="/subscription", tags=["subscription"])


# ============ Pydantic Models ============

class SubscriptionResponse(BaseModel):
    """订阅信息响应"""
    feature_tier: str
    billing_plan: Optional[str] = None
    has_active_subscription: bool
    current_plan: str
    current_period: Optional[str] = None
    status: str
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    auto_renew: bool
    quota: Dict[str, int]


class QuotaDetailsResponse(BaseModel):
    """配额详情响应"""
    plan_quota: int
    plan_used: int
    plan_remaining: int
    pack_quota: int
    pack_remaining: int
    total_remaining: int
    packs: List[Dict[str, Any]]


class UpgradeSubscriptionRequest(BaseModel):
    """升级订阅请求"""
    plan: str = Field(..., description="Plan: pro, ultra")
    period: str = Field(..., description="Period: monthly, quarterly, yearly")


class UpgradeSubscriptionResponse(BaseModel):
    """升级订阅响应"""
    order_id: str
    status: str
    amount: int
    message: str


class CancelSubscriptionResponse(BaseModel):
    """取消订阅响应"""
    success: bool
    message: str
    current_period_end: Optional[str] = None


class PurchaseQuotaPackRequest(BaseModel):
    """购买额度包请求"""
    pack_type: str = Field(..., description="Pack type: pack_10, pack_50")


class PurchaseQuotaPackResponse(BaseModel):
    """购买额度包响应"""
    order_id: str
    pack_id: int
    quota: int
    expires_at: str
    message: str


class UseQuotaRequest(BaseModel):
    """消耗配额请求"""
    amount: int = Field(1, ge=1, le=100, description="Amount to consume")


class UseQuotaResponse(BaseModel):
    """消耗配额响应"""
    success: bool
    message: str
    quota_status: Optional[Dict[str, Any]] = None


# ============ Subscription Routes ============

@router.get("", response_model=SubscriptionResponse)
async def get_subscription(
    current_user_id: int = Depends(get_current_user)
):
    """
    获取当前用户订阅信息

    - 返回用户的订阅状态、方案和配额信息
    """
    from backend.api.services.subscription_service import SubscriptionService

    async with get_async_db_session() as session:
        service = SubscriptionService(session)
        subscription_info = await service.get_user_subscription(current_user_id)

        if not subscription_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        return SubscriptionResponse(**subscription_info)


@router.post("/upgrade", response_model=UpgradeSubscriptionResponse)
async def upgrade_subscription(
    request: UpgradeSubscriptionRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    升级/降级订阅（模拟支付）

    - plan: 目标方案 (pro, ultra)
    - period: 计费周期 (monthly, quarterly, yearly)
    """
    # Validate plan
    if request.plan not in ["pro", "ultra"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan. Must be 'pro' or 'ultra'"
        )

    # Validate period
    if request.period not in ["monthly", "quarterly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Must be 'monthly', 'quarterly', or 'yearly'"
        )

    from backend.api.services.subscription_service import SubscriptionService

    async with get_async_db_session() as session:
        service = SubscriptionService(session)
        result = await service.upgrade_subscription(
            user_id=current_user_id,
            plan=request.plan,
            period=request.period
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Upgrade failed")
            )

        return UpgradeSubscriptionResponse(**result)


@router.post("/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    current_user_id: int = Depends(get_current_user)
):
    """
    取消订阅

    - 取消后当前周期内权益保留
    - 不会立即退款
    """
    from backend.api.services.subscription_service import SubscriptionService

    async with get_async_db_session() as session:
        service = SubscriptionService(session)
        result = await service.cancel_subscription(current_user_id)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Cancellation failed")
            )

        return CancelSubscriptionResponse(**result)


# ============ Quota Routes ============

@router.get("/quota", response_model=QuotaDetailsResponse)
async def get_quota(
    current_user_id: int = Depends(get_current_user)
):
    """
    获取配额详情

    - 返回月度配额和额度包的详细使用情况
    """
    from backend.api.services.subscription_service import SubscriptionService

    async with get_async_db_session() as session:
        service = SubscriptionService(session)
        quota_details = await service.get_quota_details(current_user_id)

        return QuotaDetailsResponse(**quota_details)


@router.post("/quota-packs/purchase", response_model=PurchaseQuotaPackResponse)
async def purchase_quota_pack(
    request: PurchaseQuotaPackRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    购买额度包（模拟支付）

    - pack_type: 额度包类型 (pack_10, pack_50)
    """
    # Validate pack type
    if request.pack_type not in ["pack_10", "pack_50"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pack type. Must be 'pack_10' or 'pack_50'"
        )

    from backend.api.services.subscription_service import SubscriptionService

    async with get_async_db_session() as session:
        service = SubscriptionService(session)
        result = await service.purchase_quota_pack(
            user_id=current_user_id,
            pack_type=request.pack_type
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Purchase failed")
            )

        return PurchaseQuotaPackResponse(**result)


@router.post("/quota/use", response_model=UseQuotaResponse)
async def use_quota(
    request: UseQuotaRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    消耗配额

    - amount: 要消耗的配额数量
    - 优先消耗月度配额，然后消耗额度包（FIFO）
    """
    from backend.api.services.subscription_service import SubscriptionService

    async with get_async_db_session() as session:
        service = SubscriptionService(session)
        result = await service.use_quota(
            user_id=current_user_id,
            amount=request.amount
        )

        return UseQuotaResponse(**result)


@router.get("/quota/check")
async def check_quota(
    amount: int = 1,
    current_user_id: int = Depends(get_current_user)
):
    """
    检查配额是否足够

    - amount: 要检查的配额数量
    - 返回配额状态而不实际消耗
    """
    from backend.api.services.subscription_service import SubscriptionService

    async with get_async_db_session() as session:
        service = SubscriptionService(session)
        quota_status = await service.check_quota(
            user_id=current_user_id,
            amount=amount
        )

        return quota_status
