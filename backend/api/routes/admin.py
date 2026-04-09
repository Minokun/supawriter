# -*- coding: utf-8 -*-
"""系统管理 API 路由（仅超级管理员）"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.api.core.dependencies import require_admin
from backend.api.services.tier_service import TierService
from backend.api.core.system_config import SystemConfig
from utils.database import Database

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ 请求模型 ============

class SystemSettingUpdate(BaseModel):
    key: str
    value: str
    type: Optional[str] = 'string'
    category: Optional[str] = 'general'
    description: Optional[str] = ''


class SystemSettingBatchUpdate(BaseModel):
    settings: List[SystemSettingUpdate]


# ============ 系统配置 CRUD ============

@router.get("/system-settings")
async def list_system_settings(
    category: Optional[str] = None,
    admin_id: int = Depends(require_admin)
):
    """获取所有系统配置（可按分类过滤）"""
    all_settings = SystemConfig.get_all(category)
    return {
        "settings": [
            {
                "key": k,
                "value": v['value'],
                "type": v.get('type', 'string'),
                "category": v.get('category', 'general'),
                "description": v.get('description', '')
            }
            for k, v in sorted(all_settings.items())
        ],
        "total": len(all_settings),
        "categories": SystemConfig.get_categories()
    }


@router.get("/system-settings/{key:path}")
async def get_system_setting(
    key: str,
    admin_id: int = Depends(require_admin)
):
    """获取单个系统配置"""
    value = SystemConfig.get(key)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置项 '{key}' 不存在"
        )
    all_settings = SystemConfig.get_all()
    entry = all_settings.get(key, {})
    return {
        "key": key,
        "value": value,
        "type": entry.get('type', 'string'),
        "category": entry.get('category', 'general'),
        "description": entry.get('description', '')
    }


@router.put("/system-settings")
async def update_system_setting(
    data: SystemSettingUpdate,
    admin_id: int = Depends(require_admin)
):
    """更新单个系统配置（实时通知所有在线客户端）"""
    success = await SystemConfig.update_and_notify(
        key=data.key,
        value=data.value,
        setting_type=data.type or 'string',
        category=data.category or 'general',
        description=data.description or ''
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新配置失败"
        )

    logger.info(f"Admin {admin_id} updated system setting: {data.key}")
    return {"message": "配置已更新", "key": data.key}


@router.put("/system-settings/batch")
async def batch_update_system_settings(
    data: SystemSettingBatchUpdate,
    admin_id: int = Depends(require_admin)
):
    """批量更新系统配置（一次广播通知）"""
    updates = [
        {
            'key': s.key,
            'value': s.value,
            'type': s.type or 'string',
            'category': s.category or 'general',
            'description': s.description or ''
        }
        for s in data.settings
    ]

    count = await SystemConfig.batch_update_and_notify(updates)
    logger.info(f"Admin {admin_id} batch updated {count} system settings")
    return {"message": f"已更新 {count} 项配置", "updated": count}


@router.delete("/system-settings/{key:path}")
async def delete_system_setting(
    key: str,
    admin_id: int = Depends(require_admin)
):
    """删除系统配置"""
    success = SystemConfig.delete(key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除配置失败"
        )

    logger.info(f"Admin {admin_id} deleted system setting: {key}")
    return {"message": "配置已删除", "key": key}


@router.post("/system-settings/reload")
async def reload_system_settings(
    admin_id: int = Depends(require_admin)
):
    """强制重新加载所有系统配置"""
    SystemConfig.reload()
    return {"message": "配置已重新加载", "total": len(SystemConfig.get_all())}


# ============ 会员等级管理 ============

@router.get("/users/{user_id}/membership")
async def get_user_membership(
    user_id: int,
    admin_id: int = Depends(require_admin)
):
    """获取用户会员等级"""
    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT id, username, membership_tier FROM users WHERE id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        return {
            "user_id": row['id'],
            "username": row['username'],
            "membership_tier": row['membership_tier']
        }


class MembershipUpdate(BaseModel):
    tier: str  # free, pro, ultra


@router.put("/users/{user_id}/membership")
async def update_user_membership(
    user_id: int,
    data: MembershipUpdate,
    admin_id: int = Depends(require_admin)
):
    """更新用户会员等级"""
    if data.tier not in ('free', 'pro', 'ultra'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的会员等级，可选值: free, pro, ultra"
        )

    with Database.get_cursor() as cursor:
        cursor.execute(
            "UPDATE users SET membership_tier = %s WHERE id = %s RETURNING id, username, membership_tier",
            (data.tier, user_id)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

    logger.info(f"Admin {admin_id} updated user {user_id} membership to {data.tier}")
    return {
        "message": "会员等级已更新",
        "user_id": row['id'],
        "username": row['username'],
        "membership_tier": row['membership_tier']
    }


# ============ 等级默认配置管理 ============

class TierDefaultsUpdate(BaseModel):
    tier: str
    default_chat_model: Optional[str] = None
    default_writer_model: Optional[str] = None
    article_limit_per_month: Optional[int] = None


@router.get("/tier-defaults")
async def get_all_tier_defaults(admin_id: int = Depends(require_admin)):
    """获取所有等级的默认配置"""
    return TierService.get_all_tier_defaults()


@router.get("/tier-defaults/{tier}")
async def get_tier_defaults(tier: str, admin_id: int = Depends(require_admin)):
    """获取指定等级的默认配置"""
    if tier not in TierService.TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的等级: {tier}"
        )

    defaults = TierService.get_tier_defaults(tier)
    if not defaults:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="等级配置不存在"
        )
    return defaults


@router.put("/tier-defaults/{tier}")
async def update_tier_defaults(
    tier: str,
    data: TierDefaultsUpdate,
    admin_id: int = Depends(require_admin)
):
    """更新等级默认配置"""
    if tier not in TierService.TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的等级: {tier}"
        )

    success = TierService.update_tier_defaults(
        tier,
        chat_model=data.default_chat_model,
        writer_model=data.default_writer_model,
        article_limit=data.article_limit_per_month
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败"
        )

    logger.info(f"Admin {admin_id} updated tier {tier} defaults")
    return {"message": "等级默认配置已更新", "tier": tier}


# ============ 全局 LLM 提供商管理 ============

class ModelConfig(BaseModel):
    name: str
    min_tier: str = "free"  # free / pro / ultra


class GlobalProviderUpdate(BaseModel):
    provider_id: str
    base_url: str
    models: List[ModelConfig]  # [{"name": "deepseek-chat", "min_tier": "free"}]
    api_key: Optional[str] = None
    enabled: bool = True


@router.get("/global-providers")
async def get_global_providers(admin_id: int = Depends(require_admin)):
    """获取全局 LLM 提供商列表"""
    return {"providers": TierService.get_global_providers()}


@router.put("/global-providers")
async def update_global_provider(data: GlobalProviderUpdate, admin_id: int = Depends(require_admin)):
    """更新或创建全局提供商"""
    # 验证 min_tier 值
    for model in data.models:
        if model.min_tier not in TierService.TIERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的 min_tier: {model.min_tier}"
            )

    # 转换为 dict 格式
    models_dict = [{"name": m.name, "min_tier": m.min_tier} for m in data.models]

    success = TierService.update_global_provider(
        data.provider_id,
        data.base_url,
        models_dict,
        data.api_key,
        data.enabled
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存失败"
        )

    logger.info(f"Admin {admin_id} updated global provider {data.provider_id}")
    return {"message": "提供商配置已保存", "provider_id": data.provider_id}


@router.delete("/global-providers/{provider_id}")
async def delete_global_provider(provider_id: str, admin_id: int = Depends(require_admin)):
    """删除全局提供商"""
    success = TierService.delete_global_provider(provider_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提供商不存在"
        )

    logger.info(f"Admin {admin_id} deleted global provider {provider_id}")
    return {"message": "提供商已删除", "provider_id": provider_id}


# ============ 用户搜索与管理 ============

@router.get("/users/search")
async def search_users(
    q: str = "",
    limit: int = 20,
    offset: int = 0,
    admin_id: int = Depends(require_admin)
):
    """搜索用户"""
    if len(q) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="搜索关键词至少需要1个字符"
        )

    users = TierService.search_users(q, limit, offset)
    return {
        "users": users,
        "total": len(users),
        "limit": limit,
        "offset": offset
    }
