# -*- coding: utf-8 -*-
"""设置相关 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
import logging
import json

from backend.api.models.settings import (
    ModelConfigUpdate, ModelConfigResponse,
    UserPreferencesUpdate, UserPreferencesResponse
)
from backend.api.core.dependencies import get_current_user, require_admin, get_user_tier
from backend.api.services.tier_service import TierService
from backend.api.core.encryption import encryption_manager
from utils.database import Database

logger = logging.getLogger(__name__)
router = APIRouter()

# ============ 模型配置 ============

@router.get("/available-models")
async def get_available_models(user_tier: str = Depends(get_user_tier)):
    """获取用户等级可用的模型列表"""
    models = TierService.get_tier_available_models(user_tier)
    return {"tier": user_tier, "models": models}


@router.get("/available-providers")
async def get_available_providers(user_tier: str = Depends(get_user_tier)):
    """获取用户可用的提供商和模型列表（非管理员端点）

    返回用户当前等级可以使用的提供商及其模型，按提供商分组。
    """
    models = TierService.get_tier_available_models(user_tier)

    # 按 provider 分组
    providers_map = {}
    for m in models:
        provider_id = m['provider']
        if provider_id not in providers_map:
            # 获取提供商的完整信息
            all_providers = TierService.get_global_providers()
            provider_info = next((p for p in all_providers if p['provider_id'] == provider_id), None)
            providers_map[provider_id] = {
                'id': provider_id,
                'provider_id': provider_id,
                'name': provider_info['provider_name'] if provider_info else provider_id,
                'base_url': provider_info['base_url'] if provider_info else '',
                'models': [],
                'enabled': provider_info.get('enabled', True) if provider_info else True
            }
        providers_map[provider_id]['models'].append({
            'name': m['model'],
            'min_tier': m['min_tier']
        })

    return {"tier": user_tier, "providers": list(providers_map.values())}


@router.get("/models", response_model=ModelConfigResponse)
async def get_model_config(
    current_user_id: int = Depends(get_current_user),
    user_tier: str = Depends(get_user_tier)
):
    """获取用户模型配置"""
    # 获取用户等级的可用模型
    available_models = TierService.get_tier_available_models(user_tier)
    provider_models = {}
    for m in available_models:
        if m['provider'] not in provider_models:
            provider_models[m['provider']] = []
        provider_models[m['provider']].append(m['model'])

    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT chat_model, writer_model, embedding_model, image_model,
                   default_temperature, default_max_tokens, default_top_p,
                   enable_streaming, enable_thinking_process
            FROM user_model_configs
            WHERE user_id = %s
        """, (current_user_id,))

        row = cursor.fetchone()

        if not row:
            # 创建默认配置，使用等级默认值
            tier_defaults = TierService.get_tier_defaults(user_tier)
            cursor.execute("""
                INSERT INTO user_model_configs
                (user_id, chat_model, writer_model, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                RETURNING chat_model, writer_model, embedding_model, image_model,
                         default_temperature, default_max_tokens, default_top_p,
                         enable_streaming, enable_thinking_process
            """, (
                current_user_id,
                tier_defaults.get('default_chat_model', 'deepseek:deepseek-chat'),
                tier_defaults.get('default_writer_model', 'deepseek:deepseek-chat')
            ))
            row = cursor.fetchone()

        return ModelConfigResponse(
            user_id=current_user_id,
            chat_model=row['chat_model'] or 'deepseek:deepseek-chat',
            writer_model=row['writer_model'] or 'deepseek:deepseek-chat',
            embedding_model=row['embedding_model'] or 'text-embedding-3-small',
            image_model=row['image_model'] or '',
            default_temperature=float(row['default_temperature'] or 0.7),
            default_max_tokens=row['default_max_tokens'] or 4000,
            default_top_p=float(row['default_top_p'] or 1.0),
            enable_streaming=bool(True if row['enable_streaming'] is None else row['enable_streaming']),
            enable_thinking_process=bool(False if row['enable_thinking_process'] is None else row['enable_thinking_process'])
        )

@router.put("/models", response_model=ModelConfigResponse)
async def update_model_config(
    data: ModelConfigUpdate,
    current_user_id: int = Depends(get_current_user)
):
    """更新用户模型配置"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有要更新的字段"
        )
    
    set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
    values = list(update_data.values()) + [current_user_id]
    
    with Database.get_cursor() as cursor:
        # 确保记录存在
        cursor.execute("""
            INSERT INTO user_model_configs (user_id, created_at, updated_at)
            VALUES (%s, NOW(), NOW())
            ON CONFLICT (user_id) DO NOTHING
        """, (current_user_id,))
        
        cursor.execute(f"""
            UPDATE user_model_configs
            SET {set_clause}, updated_at = NOW()
            WHERE user_id = %s
            RETURNING chat_model, writer_model, embedding_model, image_model,
                     default_temperature, default_max_tokens, default_top_p,
                     enable_streaming, enable_thinking_process
        """, values)
        
        row = cursor.fetchone()
        
        logger.info(f"Model config updated for user {current_user_id}")
        
        return ModelConfigResponse(
            user_id=current_user_id,
            chat_model=row['chat_model'] or 'deepseek:deepseek-chat',
            writer_model=row['writer_model'] or 'deepseek:deepseek-chat',
            embedding_model=row['embedding_model'] or 'text-embedding-3-small',
            image_model=row['image_model'] or '',
            default_temperature=float(row['default_temperature'] or 0.7),
            default_max_tokens=row['default_max_tokens'] or 4000,
            default_top_p=float(row['default_top_p'] or 1.0),
            enable_streaming=bool(True if row['enable_streaming'] is None else row['enable_streaming']),
            enable_thinking_process=bool(False if row['enable_thinking_process'] is None else row['enable_thinking_process'])
        )

# ============ LLM 提供商配置 ============

@router.get("/llm-provider-templates")
async def get_llm_provider_templates(
    active_only: bool = True
):
    """获取系统级 LLM 提供商模板列表（无需认证）"""
    with Database.get_cursor() as cursor:
        if active_only:
            cursor.execute("""
                SELECT provider_id, provider_name, base_url, default_models, category, description, requires_api_key
                FROM llm_provider_templates
                WHERE is_active = TRUE
                ORDER BY category, provider_id
            """)
        else:
            cursor.execute("""
                SELECT provider_id, provider_name, base_url, default_models, category, description, requires_api_key
                FROM llm_provider_templates
                ORDER BY category, provider_id
            """)
        rows = cursor.fetchall()

        return {
            "templates": [
                {
                    "id": row['provider_id'],
                    "name": row['provider_name'],
                    "base_url": row['base_url'],
                    "default_models": row['default_models'] or [],
                    "category": row['category'],
                    "description": row['description'],
                    "requires_api_key": row['requires_api_key']
                }
                for row in rows
            ]
        }


def _initialize_user_providers_from_templates(user_id: int):
    """为新用户从模板初始化默认提供商配置"""
    with Database.get_cursor() as cursor:
        # 获取启用的模板
        cursor.execute("""
            SELECT provider_id, provider_name, base_url, default_models
            FROM llm_provider_templates
            WHERE is_active = TRUE
            ORDER BY category, provider_id
        """)
        templates = cursor.fetchall()

        # 插入到用户配置（默认禁用）
        for template in templates:
            cursor.execute("""
                INSERT INTO llm_providers
                (user_id, provider_id, provider_name, base_url, models, enabled)
                VALUES (%s, %s, %s, %s, %s::jsonb, FALSE)
            """, (
                user_id,
                template['provider_id'],
                template['provider_name'],
                template['base_url'],
                json.dumps(template['default_models'])
            ))
        logger.info(f"Initialized {len(templates)} providers for user {user_id}")


@router.get("/llm-providers")
async def get_llm_providers(admin_id: int = Depends(require_admin)):
    """获取全局 LLM 提供商配置（仅管理员）"""
    providers = TierService.get_global_providers()
    return {"providers": providers}


@router.put("/llm-providers")
async def update_llm_providers(
    data: dict,
    admin_id: int = Depends(require_admin)
):
    """更新全局 LLM 提供商配置（仅管理员）

    支持两种格式：
    1. 单个提供商: { "provider_id": "...", "base_url": "...", "models": [...], ... }
    2. 批量更新: { "providers": [{ "id": "...", "base_url": "...", "models": [...], ... }, ...] }
    """
    # 判断是批量更新还是单个更新
    providers_data = data.get('providers', [])

    if not providers_data:
        # 单个提供商更新
        if 'provider_id' not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少 provider_id 或 providers 字段"
            )
        providers_data = [data]

    updated_count = 0
    for provider in providers_data:
        # 优先使用 provider_id（字符串），其次使用 id
        # 注意：id 可能是数据库整数主键，provider_id 才是真正的提供商标识
        provider_id = provider.get('provider_id') or provider.get('id')
        if not provider_id:
            continue

        # 确保 provider_id 是字符串类型
        provider_id = str(provider_id)

        # 规范化 models 格式为 [{"name": "...", "min_tier": "..."}]
        models = provider.get('models', [])
        normalized_models = []
        for model in models:
            if isinstance(model, str):
                normalized_models.append({"name": model, "min_tier": "free"})
            elif isinstance(model, dict):
                model_name = model.get('name', model.get('model', ''))
                model_tier = model.get('min_tier', 'free')
                # 验证 min_tier 值
                if model_tier not in TierService.TIERS:
                    model_tier = 'free'
                normalized_models.append({
                    "name": model_name,
                    "min_tier": model_tier
                })

        success = TierService.update_global_provider(
            provider_id,
            provider.get('base_url', ''),
            normalized_models,
            provider.get('api_key'),
            provider.get('enabled', True)
        )

        if success:
            updated_count += 1

    if updated_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存失败"
        )

    logger.info(f"LLM providers updated by admin {admin_id}: {updated_count} providers")
    return {"message": "保存成功", "updated": updated_count}

# ============ 其他服务配置 ============

@router.get("/services")
async def get_service_configs(admin_id: int = Depends(require_admin)):
    """获取其他服务配置（仅管理员）"""
    from backend.api.core.system_config import SystemConfig

    # 从 system_settings 表读取配置
    qiniu_domain = SystemConfig.get('qiniu.domain', '')
    qiniu_folder = SystemConfig.get('qiniu.folder', 'supawriter/')
    qiniu_region = SystemConfig.get('qiniu.region', 'z2')
    qiniu_bucket = SystemConfig.get('qiniu.bucket', '')
    qiniu_access_key = SystemConfig.get('qiniu.access_key', '')
    qiniu_secret_key = SystemConfig.get('qiniu.secret_key', '')
    serper_api_key = SystemConfig.get('serper.api_key', '')

    # 嵌入向量配置
    embedding_model = SystemConfig.get('embedding.model', 'Qwen3-VL-Embedding-8B')
    embedding_provider = SystemConfig.get('embedding.default_provider', 'gitee')
    embedding_dimension = SystemConfig.get('embedding.dimension', '2048')
    embedding_gitee_base_url = SystemConfig.get('embedding.gitee.base_url', 'https://ai.gitee.com/v1')
    embedding_gitee_api_key = SystemConfig.get('embedding.gitee.api_key', '')
    # Masked API key for display
    embedding_gitee_api_key_masked = ''
    if embedding_gitee_api_key and len(embedding_gitee_api_key) > 8:
        embedding_gitee_api_key_masked = embedding_gitee_api_key[:4] + '••••••••' + embedding_gitee_api_key[-4:]
    elif embedding_gitee_api_key:
        embedding_gitee_api_key_masked = embedding_gitee_api_key[:2] + '••••'

    return {
        "qiniu_domain": qiniu_domain,
        "qiniu_folder": qiniu_folder,
        "qiniu_region": qiniu_region,
        "qiniu_bucket": qiniu_bucket,
        "qiniu_access_key": qiniu_access_key,
        "qiniu_secret_key": qiniu_secret_key,
        "qiniu_key_set": bool(qiniu_access_key and qiniu_secret_key),
        "serper_api_key": serper_api_key,
        "serper_key_set": bool(serper_api_key),
        "embedding_model": embedding_model,
        "embedding_provider": embedding_provider,
        "embedding_dimension": str(embedding_dimension) if embedding_dimension else '2048',
        "embedding_gitee_base_url": embedding_gitee_base_url,
        "embedding_gitee_api_key": embedding_gitee_api_key_masked,
        "embedding_key_set": bool(embedding_gitee_api_key),
    }


@router.put("/services")
async def update_service_configs(
    data: dict,
    admin_id: int = Depends(require_admin)
):
    """更新其他服务配置（仅管理员）"""
    from backend.api.core.system_config import SystemConfig

    updates = []

    # 七牛云配置
    if 'qiniu_domain' in data:
        updates.append({
            'key': 'qiniu.domain',
            'value': data['qiniu_domain'],
            'type': 'string',
            'category': 'qiniu',
            'description': '七牛云 CDN 域名'
        })
    if 'qiniu_folder' in data:
        updates.append({
            'key': 'qiniu.folder',
            'value': data['qiniu_folder'],
            'type': 'string',
            'category': 'qiniu',
            'description': '七牛云存储路径前缀'
        })
    if 'qiniu_region' in data:
        updates.append({
            'key': 'qiniu.region',
            'value': data['qiniu_region'],
            'type': 'string',
            'category': 'qiniu',
            'description': '七牛云存储区域'
        })
    if 'qiniu_bucket' in data:
        updates.append({
            'key': 'qiniu.bucket',
            'value': data['qiniu_bucket'],
            'type': 'string',
            'category': 'qiniu',
            'description': '七牛云存储空间名称'
        })
    # 敏感信息只有在新值非空时才更新
    if data.get('qiniu_access_key'):
        updates.append({
            'key': 'qiniu.access_key',
            'value': data['qiniu_access_key'],
            'type': 'secret',
            'category': 'qiniu',
            'description': '七牛云 Access Key'
        })
    if data.get('qiniu_secret_key'):
        updates.append({
            'key': 'qiniu.secret_key',
            'value': data['qiniu_secret_key'],
            'type': 'secret',
            'category': 'qiniu',
            'description': '七牛云 Secret Key'
        })

    # SERPER API Key
    if data.get('serper_api_key'):
        updates.append({
            'key': 'serper.api_key',
            'value': data['serper_api_key'],
            'type': 'secret',
            'category': 'search',
            'description': 'SERPER 搜索 API Key'
        })

    # 嵌入向量配置
    if 'embedding_model' in data:
        updates.append({
            'key': 'embedding.model',
            'value': data['embedding_model'],
            'type': 'string',
            'category': 'embedding',
            'description': '嵌入向量模型'
        })
    if 'embedding_provider' in data:
        updates.append({
            'key': 'embedding.default_provider',
            'value': data['embedding_provider'],
            'type': 'string',
            'category': 'embedding',
            'description': '嵌入向量默认提供商'
        })
    if 'embedding_dimension' in data:
        updates.append({
            'key': 'embedding.dimension',
            'value': str(data['embedding_dimension']),
            'type': 'string',
            'category': 'embedding',
            'description': '嵌入向量维度'
        })
    if 'embedding_gitee_base_url' in data:
        updates.append({
            'key': 'embedding.gitee.base_url',
            'value': data['embedding_gitee_base_url'],
            'type': 'string',
            'category': 'embedding',
            'description': 'Gitee 嵌入向量 Base URL'
        })
    # 跳过 masked 宯值（包含 • 字符的），不以覆盖真实密钥
    embedding_api_key = data.get('embedding_gitee_api_key', '')
    if embedding_api_key and '•' not in embedding_api_key:
        updates.append({
            'key': 'embedding.gitee.api_key',
            'value': embedding_api_key,
            'type': 'secret',
            'category': 'embedding',
            'description': 'Gitee 嵌入向量 API Key'
        })

    # 批量更新
    count = await SystemConfig.batch_update_and_notify(updates)

    logger.info(f"Service configs updated by admin {admin_id}: {count} items")
    return {"message": "保存成功", "updated": count}

# ============ 用户偏好 ============

@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(current_user_id: int = Depends(get_current_user)):
    """获取用户偏好"""
    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT editor_font_size, editor_theme, auto_save_interval,
                   default_article_style, default_article_length, default_language,
                   sidebar_collapsed, theme_mode,
                   email_notifications, task_complete_notification
            FROM user_preferences
            WHERE user_id = %s
        """, (current_user_id,))
        
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("""
                INSERT INTO user_preferences (user_id)
                VALUES (%s)
                RETURNING editor_font_size, editor_theme, auto_save_interval,
                         default_article_style, default_article_length, default_language,
                         sidebar_collapsed, theme_mode,
                         email_notifications, task_complete_notification
            """, (current_user_id,))
            row = cursor.fetchone()
        
        return UserPreferencesResponse(
            user_id=current_user_id,
            editor_font_size=row['editor_font_size'],
            editor_theme=row['editor_theme'],
            auto_save_interval=row['auto_save_interval'],
            default_article_style=row['default_article_style'],
            default_article_length=row['default_article_length'],
            default_language=row['default_language'],
            sidebar_collapsed=row['sidebar_collapsed'],
            theme_mode=row['theme_mode'],
            email_notifications=row['email_notifications'],
            task_complete_notification=row['task_complete_notification']
        )

@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    data: UserPreferencesUpdate,
    current_user_id: int = Depends(get_current_user)
):
    """更新用户偏好"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有要更新的字段"
        )
    
    set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
    values = list(update_data.values()) + [current_user_id]
    
    with Database.get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO user_preferences (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING
        """, (current_user_id,))
        
        cursor.execute(f"""
            UPDATE user_preferences
            SET {set_clause}, updated_at = NOW()
            WHERE user_id = %s
            RETURNING editor_font_size, editor_theme, auto_save_interval,
                     default_article_style, default_article_length, default_language,
                     sidebar_collapsed, theme_mode,
                     email_notifications, task_complete_notification
        """, values)
        
        row = cursor.fetchone()
        
        logger.info(f"Preferences updated for user {current_user_id}")
        
        return UserPreferencesResponse(
            user_id=current_user_id,
            editor_font_size=row['editor_font_size'],
            editor_theme=row['editor_theme'],
            auto_save_interval=row['auto_save_interval'],
            default_article_style=row['default_article_style'],
            default_article_length=row['default_article_length'],
            default_language=row['default_language'],
            sidebar_collapsed=row['sidebar_collapsed'],
            theme_mode=row['theme_mode'],
            email_notifications=row['email_notifications'],
            task_complete_notification=row['task_complete_notification']
        )
