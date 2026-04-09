# -*- coding: utf-8 -*-
"""
统一系统配置读取服务

所有业务配置从 system_settings 表读取，带内存缓存。
配置变更时通过 WebSocket 广播通知所有在线客户端。

配置分层：
  .env → 仅基础设施（DB, Redis, JWT 等）
  system_settings 表 → 所有业务配置
  用户级表 → 覆盖系统默认值
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SystemConfig:
    """
    统一系统配置读取（带内存缓存 + WebSocket 失效通知）

    用法：
        SystemConfig.get('search.default_spider_num', '20')
        SystemConfig.get_int('embedding.dimension', 2048)
        SystemConfig.get_bool('article.default_enable_images', True)
        SystemConfig.get_json('article.process_config', {})
        SystemConfig.get_tier_config('article_daily_limit', tier='pro')
    """

    _cache: Dict[str, Dict[str, Any]] = {}  # key -> {value, type, category, description}
    _loaded: bool = False
    _schema_mode: Optional[str] = None

    # ========== 读取接口 ==========

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """读取字符串配置"""
        cls._ensure_loaded()
        entry = cls._cache.get(key)
        if entry is not None:
            return entry['value']
        return default

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        """读取整数配置"""
        val = cls.get(key)
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        """读取布尔配置"""
        val = cls.get(key)
        if val is None:
            return default
        return val.lower() in ('true', '1', 'yes')

    @classmethod
    def get_json(cls, key: str, default: Any = None) -> Any:
        """读取 JSON 配置"""
        val = cls.get(key)
        if val is None:
            return default
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default

    @classmethod
    def get_tier_config(cls, key: str, tier: str = 'free') -> Optional[str]:
        """
        读取会员等级相关配置

        Args:
            key: 配置键（不含 quota.{tier}. 前缀），如 'article_daily_limit'
            tier: 会员等级 'free' / 'pro' / 'ultra'
        """
        return cls.get(f'quota.{tier}.{key}')

    @classmethod
    def get_tier_config_int(cls, key: str, tier: str = 'free', default: int = 0) -> int:
        """读取会员等级整数配置"""
        return cls.get_int(f'quota.{tier}.{key}', default)

    @classmethod
    def get_all(cls, category: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        获取所有配置（可按 category 过滤）

        Returns:
            {key: {value, type, category, description}, ...}
        """
        cls._ensure_loaded()
        if category is None:
            return dict(cls._cache)
        return {k: v for k, v in cls._cache.items() if v.get('category') == category}

    @classmethod
    def get_categories(cls) -> List[str]:
        """获取所有配置分类"""
        cls._ensure_loaded()
        return sorted(set(v.get('category', 'general') for v in cls._cache.values()))

    # ========== 写入接口 ==========

    @classmethod
    def set(cls, key: str, value: str, setting_type: str = 'string',
            category: str = 'general', description: str = '') -> bool:
        """
        写入配置到数据库并更新缓存

        Args:
            key: 配置键
            value: 配置值
            setting_type: 值类型 (string/integer/boolean/json)
            category: 分类
            description: 描述
        """
        try:
            cls._execute_set(key, value, setting_type, category, description)

            # 更新本地缓存
            cls._cache[key] = {
                'value': value,
                'type': setting_type,
                'category': category,
                'description': description
            }
            return True

        except Exception as e:
            logger.error(f"Failed to set system config '{key}': {e}")
            return False

    @classmethod
    async def update_and_notify(cls, key: str, value: str,
                                setting_type: str = 'string',
                                category: str = 'general',
                                description: str = '') -> bool:
        """
        更新配置并通过 WebSocket 广播通知所有在线客户端

        Args:
            key: 配置键
            value: 新值
            setting_type: 值类型
            category: 分类
            description: 描述
        """
        success = cls.set(key, value, setting_type, category, description)
        if not success:
            return False

        # WebSocket 广播
        try:
            from backend.api.core.websocket import manager
            await manager.broadcast({
                "type": "config_changed",
                "key": key,
                "category": category,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            logger.info(f"Config changed and broadcast: {key}")
        except Exception as e:
            logger.warning(f"Config updated but WebSocket broadcast failed: {e}")

        return True

    @classmethod
    async def batch_update_and_notify(cls, updates: List[Dict[str, str]]) -> int:
        """
        批量更新配置并广播一次通知

        Args:
            updates: [{'key': ..., 'value': ..., 'type': ..., 'category': ..., 'description': ...}, ...]

        Returns:
            成功更新的数量
        """
        count = 0
        changed_keys = []
        for item in updates:
            success = cls.set(
                key=item['key'],
                value=item['value'],
                setting_type=item.get('type', 'string'),
                category=item.get('category', 'general'),
                description=item.get('description', '')
            )
            if success:
                count += 1
                changed_keys.append(item['key'])

        # 广播一次通知
        if changed_keys:
            try:
                from backend.api.core.websocket import manager
                await manager.broadcast({
                    "type": "config_changed",
                    "keys": changed_keys,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.warning(f"Batch config broadcast failed: {e}")

        return count

    @classmethod
    def delete(cls, key: str) -> bool:
        """删除配置"""
        try:
            cls._execute_delete(key)

            cls._cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Failed to delete system config '{key}': {e}")
            return False

    # ========== 缓存管理 ==========

    @classmethod
    def invalidate(cls):
        """清除缓存，强制下次读取时重新加载"""
        cls._cache.clear()
        cls._loaded = False
        cls._schema_mode = None
        logger.debug("SystemConfig cache invalidated")

    @classmethod
    def reload(cls):
        """强制重新加载所有配置"""
        cls._loaded = False
        cls._cache.clear()
        cls._schema_mode = None
        cls._load_all()

    @classmethod
    def _detect_schema_mode(cls) -> str:
        if cls._schema_mode is not None:
            return cls._schema_mode

        from utils.database import Database

        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'system_settings'
            """)
            columns = {row['column_name'] for row in cursor.fetchall()}

        cls._schema_mode = 'legacy' if {'key', 'value'}.issubset(columns) else 'modern'
        return cls._schema_mode

    @classmethod
    def _ensure_loaded(cls):
        """确保配置已加载"""
        if not cls._loaded:
            cls._load_all()

    @classmethod
    def _load_all(cls):
        """从数据库一次性加载所有 system_settings"""
        try:
            from utils.database import Database
            schema_mode = cls._detect_schema_mode()

            with Database.get_cursor() as cursor:
                if schema_mode == 'legacy':
                    cursor.execute("""
                        SELECT key, value,
                               COALESCE(category, 'general') as category,
                               COALESCE(description, '') as description
                        FROM system_settings
                        ORDER BY key
                    """)
                else:
                    cursor.execute("""
                        SELECT setting_key, setting_value, setting_type, 
                               COALESCE(category, 'general') as category, 
                               COALESCE(description, '') as description
                        FROM system_settings
                        ORDER BY setting_key
                    """)
                rows = cursor.fetchall()

            cls._cache.clear()
            for row in rows:
                key = row['key'] if schema_mode == 'legacy' else row['setting_key']
                value = row['value'] if schema_mode == 'legacy' else row['setting_value']
                cls._cache[key] = {
                    'value': value,
                    'type': row.get('setting_type', 'string'),
                    'category': row['category'],
                    'description': row['description']
                }

            cls._loaded = True
            logger.info(f"SystemConfig loaded: {len(cls._cache)} settings")

        except Exception as e:
            logger.error(f"Failed to load system settings: {e}")
            cls._loaded = False

    @classmethod
    def _execute_set(cls, key: str, value: str, setting_type: str, category: str, description: str):
        from utils.database import Database

        schema_mode = cls._detect_schema_mode()
        with Database.get_cursor() as cursor:
            if schema_mode == 'legacy':
                cursor.execute("""
                    INSERT INTO system_settings (key, value, category, description)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        category = COALESCE(EXCLUDED.category, system_settings.category),
                        description = COALESCE(EXCLUDED.description, system_settings.description),
                        updated_at = NOW()
                """, (key, value, category, description))
            else:
                cursor.execute("""
                    INSERT INTO system_settings 
                    (setting_key, setting_value, setting_type, category, description)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (setting_key) DO UPDATE
                    SET setting_value = EXCLUDED.setting_value,
                        setting_type = COALESCE(EXCLUDED.setting_type, system_settings.setting_type),
                        category = COALESCE(EXCLUDED.category, system_settings.category),
                        description = COALESCE(EXCLUDED.description, system_settings.description),
                        updated_at = NOW()
                """, (key, value, setting_type, category, description))

    @classmethod
    def _execute_delete(cls, key: str):
        from utils.database import Database

        schema_mode = cls._detect_schema_mode()
        with Database.get_cursor() as cursor:
            if schema_mode == 'legacy':
                cursor.execute("DELETE FROM system_settings WHERE key = %s", (key,))
            else:
                cursor.execute("DELETE FROM system_settings WHERE setting_key = %s", (key,))
