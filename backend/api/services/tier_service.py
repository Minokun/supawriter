# -*- coding: utf-8 -*-
"""会员等级和模型权限服务"""

import os
from typing import List, Dict, Optional, Any
import logging
from utils.database import Database
from backend.api.core.encryption import encryption_manager

logger = logging.getLogger(__name__)


def get_super_admin_emails() -> List[str]:
    """从环境变量获取超级管理员邮箱列表"""
    emails_str = os.getenv('SUPER_ADMIN_EMAILS', 'wxk952718180@gmail.com')
    return [email.strip() for email in emails_str.split(',') if email.strip()]


class TierService:
    """会员等级配置服务"""

    # 会员等级定义（数值越大权限越高）
    # superuser: 系统超级管理员，只能脚本设置，拥有所有权限
    TIERS = ['free', 'pro', 'ultra', 'superuser']
    TIER_LEVELS = {
        'free': 0,
        'pro': 1,
        'ultra': 2,
        'superuser': 3  # 超级管理员，最高权限
    }

    # 默认文章配额
    DEFAULT_QUOTAS = {
        'free': 5,
        'pro': 20,
        'ultra': 60
    }

    @staticmethod
    def is_superuser(user_id: int) -> bool:
        """检查用户是否为超级管理员"""
        super_admin_emails = get_super_admin_emails()
        with Database.get_cursor() as cursor:
            cursor.execute(
                "SELECT email, is_superuser FROM users WHERE id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False
            return row['email'] in super_admin_emails and row['is_superuser']

    @staticmethod
    def get_user_tier(user_id: int) -> str:
        """获取用户会员等级"""
        with Database.get_cursor() as cursor:
            cursor.execute(
                "SELECT membership_tier FROM users WHERE id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
            return row['membership_tier'] if row else 'free'

    @staticmethod
    def get_tier_available_models(tier: str) -> List[Dict[str, str]]:
        """获取指定等级可用的模型列表（自动继承低等级模型）

        通过比较用户等级数值和模型的 min_tier 数值，自动实现等级继承：
        - ultra 用户可以看到所有 min_tier <= 2 的模型
        - pro 用户可以看到所有 min_tier <= 1 的模型
        - free 用户只能看到 min_tier <= 0 的模型
        """
        tier_level = TierService.TIER_LEVELS.get(tier, 0)
        result = []

        for provider in TierService.get_global_providers():
            for model in provider.get('models', []):
                model_min_tier = model.get('min_tier', 'free')
                model_tier_level = TierService.TIER_LEVELS.get(model_min_tier, 0)

                # 用户等级 >= 模型最低等级时，该模型可用
                if tier_level >= model_tier_level:
                    result.append({
                        "provider": provider['provider_id'],
                        "model": model['name'],
                        "min_tier": model_min_tier
                    })

        return result

    @staticmethod
    def get_all_models_with_tier_info() -> List[Dict[str, Any]]:
        """获取所有模型及其等级信息（用于前端展示，包括不可选的模型）"""
        result = []
        for provider in TierService.get_global_providers():
            for model in provider.get('models', []):
                result.append({
                    "provider": provider['provider_id'],
                    "model": model['name'],
                    "min_tier": model.get('min_tier', 'free'),
                    "enabled": provider.get('enabled', True)
                })
        return result

    @staticmethod
    def get_tier_defaults(tier: str) -> Optional[Dict[str, Any]]:
        """获取指定等级的默认配置"""
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT tier, default_chat_model, default_writer_model, article_limit_per_month, updated_at
                FROM tier_default_models
                WHERE tier = %s
            """, (tier,))
            row = cursor.fetchone()
            if row:
                return {
                    "tier": row['tier'],
                    "default_chat_model": row['default_chat_model'],
                    "default_writer_model": row['default_writer_model'],
                    "article_limit_per_month": row['article_limit_per_month'],
                    "updated_at": row['updated_at']
                }
            return None

    @staticmethod
    def get_all_tier_defaults() -> Dict[str, Dict[str, Any]]:
        """获取所有等级的默认配置"""
        result = {}
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT tier, default_chat_model, default_writer_model, article_limit_per_month, updated_at
                FROM tier_default_models
                ORDER BY tier
            """)
            for row in cursor.fetchall():
                result[row['tier']] = {
                    "default_chat_model": row['default_chat_model'],
                    "default_writer_model": row['default_writer_model'],
                    "article_limit_per_month": row['article_limit_per_month'],
                    "updated_at": row['updated_at']
                }
        return result

    @staticmethod
    def update_tier_defaults(tier: str, chat_model: Optional[str] = None,
                           writer_model: Optional[str] = None,
                           article_limit: Optional[int] = None) -> bool:
        """更新等级默认配置"""
        if tier not in TierService.TIERS:
            return False

        update_fields = []
        values = []
        if chat_model is not None:
            update_fields.append("default_chat_model = %s")
            values.append(chat_model)
        if writer_model is not None:
            update_fields.append("default_writer_model = %s")
            values.append(writer_model)
        if article_limit is not None:
            update_fields.append("article_limit_per_month = %s")
            values.append(article_limit)

        if not update_fields:
            return True

        update_fields.append("updated_at = NOW()")
        values.append(tier)

        with Database.get_cursor() as cursor:
            cursor.execute(f"""
                UPDATE tier_default_models
                SET {', '.join(update_fields)}
                WHERE tier = %s
                RETURNING tier
            """, values)
            return cursor.fetchone() is not None

    @staticmethod
    def get_global_providers() -> List[Dict[str, Any]]:
        """获取全局 LLM 提供商列表"""
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, provider_id, provider_name, base_url, models, enabled, api_key_encrypted
                FROM global_llm_providers
                ORDER BY provider_id
            """)
            return [
                {
                    "id": row['provider_id'],  # 使用 provider_id 作为前端 id
                    "provider_id": row['provider_id'],
                    "provider_name": row['provider_name'],
                    "name": row['provider_name'],  # 添加 name 字段供前端使用
                    "base_url": row['base_url'],
                    "models": row['models'] or [],
                    "enabled": row['enabled'],
                    # 如果有加密密钥，返回占位符表示已设置
                    "api_key": "••••••••" if row['api_key_encrypted'] else ""
                }
                for row in cursor.fetchall()
            ]

    @staticmethod
    def get_provider_credentials(provider_id: str) -> Optional[Dict[str, Any]]:
        """获取提供商的凭据信息（包括解密后的 API key）

        供后端服务调用，不返回给前端

        Args:
            provider_id: 提供商标识

        Returns:
            包含 base_url, api_key, models 的字典，如果提供商不存在或未启用则返回 None
        """
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT provider_id, provider_name, base_url, api_key_encrypted, models, enabled
                FROM global_llm_providers
                WHERE provider_id = %s AND enabled = TRUE
            """, (provider_id,))
            row = cursor.fetchone()

            if not row:
                return None

            # 解密 API key
            api_key = ""
            if row['api_key_encrypted']:
                try:
                    api_key = encryption_manager.decrypt(row['api_key_encrypted'])
                except Exception as e:
                    logger.error(f"解密 API key 失败: {provider_id}, {e}")

            return {
                "provider_id": row['provider_id'],
                "provider_name": row['provider_name'],
                "base_url": row['base_url'],
                "api_key": api_key,
                "models": row['models'] or []
            }

    @staticmethod
    def get_all_provider_credentials() -> Dict[str, Dict[str, Any]]:
        """获取所有已启用提供商的凭据信息

        Returns:
            以 provider_id 为 key 的凭据字典
        """
        result = {}
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT provider_id, provider_name, base_url, api_key_encrypted, models
                FROM global_llm_providers
                WHERE enabled = TRUE
            """)

            for row in cursor.fetchall():
                # 解密 API key
                api_key = ""
                if row['api_key_encrypted']:
                    try:
                        api_key = encryption_manager.decrypt(row['api_key_encrypted'])
                    except Exception as e:
                        logger.error(f"解密 API key 失败: {row['provider_id']}, {e}")
                        continue  # 跳过解密失败的提供商

                if api_key:  # 只返回有 API key 的提供商
                    result[row['provider_id']] = {
                        "provider_name": row['provider_name'],
                        "base_url": row['base_url'],
                        "api_key": api_key,
                        "models": row['models'] or []
                    }

        return result

    @staticmethod
    def update_global_provider(provider_id: str, base_url: str,
                             models: List[Dict[str, str]],  # [{"name": "...", "min_tier": "..."}]
                             api_key: Optional[str] = None, enabled: bool = True) -> bool:
        """更新或创建全局提供商

        models 结构: [{"name": "deepseek-chat", "min_tier": "free"}, ...]
        """
        api_key_encrypted = None
        if api_key:
            api_key_encrypted = encryption_manager.encrypt(api_key)
        else:
            # 保留现有密钥
            with Database.get_cursor() as cursor:
                cursor.execute(
                    "SELECT api_key_encrypted FROM global_llm_providers WHERE provider_id = %s",
                    (provider_id,)
                )
                row = cursor.fetchone()
                if row:
                    api_key_encrypted = row['api_key_encrypted']

        import json
        with Database.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO global_llm_providers
                (provider_id, provider_name, base_url, api_key_encrypted, models, enabled)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (provider_id)
                DO UPDATE SET
                    base_url = EXCLUDED.base_url,
                    api_key_encrypted = COALESCE(EXCLUDED.api_key_encrypted, global_llm_providers.api_key_encrypted),
                    models = EXCLUDED.models,
                    enabled = EXCLUDED.enabled,
                    updated_at = NOW()
                RETURNING id
            """, (
                provider_id,
                provider_id,
                base_url,
                api_key_encrypted,
                json.dumps(models),
                enabled
            ))
            return cursor.fetchone() is not None

    @staticmethod
    def delete_global_provider(provider_id: str) -> bool:
        """删除全局提供商"""
        with Database.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM global_llm_providers WHERE provider_id = %s",
                (provider_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def search_users(query: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索用户（管理员功能）"""
        with Database.get_cursor() as cursor:
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT id, username, email, display_name, membership_tier, is_superuser, created_at
                FROM users
                WHERE username ILIKE %s OR email ILIKE %s OR display_name ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (search_pattern, search_pattern, search_pattern, limit, offset))
            return [
                {
                    "id": row['id'],
                    "username": row['username'],
                    "email": row['email'],
                    "display_name": row['display_name'],
                    "membership_tier": row['membership_tier'],
                    "is_superuser": row['is_superuser'],
                    "created_at": row['created_at']
                }
                for row in cursor.fetchall()
            ]

    @staticmethod
    def update_user_tier(user_id: int, tier: str) -> bool:
        """更新用户会员等级（管理员功能）"""
        if tier not in TierService.TIERS:
            return False

        with Database.get_cursor() as cursor:
            cursor.execute("""
                UPDATE users
                SET membership_tier = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """, (tier, user_id))
            success = cursor.fetchone() is not None
            if success:
                logger.info(f"User {user_id} tier updated to {tier}")
            return success

    @staticmethod
    def check_user_quota(user_id: int) -> Dict[str, Any]:
        """检查用户文章配额（关联文章表自动统计）

        Returns:
            {
                "allowed": bool,  # 是否可以继续生成
                "used": int,      # 本月已用次数
                "limit": int,     # 配额上限
                "remaining": int  # 剩余次数
            }
        """
        tier = TierService.get_user_tier(user_id)

        # superuser 拥有无限配额
        if tier == 'superuser':
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM articles
                    WHERE user_id = %s
                    AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                """, (user_id,))
                row = cursor.fetchone()
                used = row['count'] if row else 0

            return {
                "allowed": True,  # superuser 永远允许
                "used": used,
                "limit": 999999,  # 显示为无限
                "remaining": 999999
            }

        tier_defaults = TierService.get_tier_defaults(tier)
        limit = tier_defaults.get('article_limit_per_month', 5) if tier_defaults else 5

        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM articles
                WHERE user_id = %s
                AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """, (user_id,))
            row = cursor.fetchone()
            used = row['count'] if row else 0

        return {
            "allowed": used < limit,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used)
        }
