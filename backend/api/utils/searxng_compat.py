# -*- coding: utf-8 -*-
"""
Backend SearXNG Compatibility Layer
提供与 searxng_utils 兼容的接口，使用 backend 配置

支持从数据库动态获取用户的 LLM 配置
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

# 添加必要的路径
backend_root = Path(__file__).parent.parent.parent.parent.parent
if str(backend_root / "backend") not in sys.path:
    sys.path.insert(0, str(backend_root / "backend"))
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# ============================================================================
# 动态用户配置管理
# ============================================================================

_current_user_id = None


def set_user_context(user_id: Optional[int] = None):
    """
    设置当前用户上下文，用于动态加载 LLM 配置

    Args:
        user_id: 用户ID，如果为 None 则使用默认用户
    """
    global _current_user_id
    _current_user_id = user_id

    # 清除缓存，强制重新加载
    _dynamic_settings.clear_cache()


def get_user_context() -> Optional[int]:
    """获取当前用户ID"""
    return _current_user_id


# ============================================================================
# 创建 settings 模块替换
# ============================================================================

class _DynamicSettings:
    """
    动态设置类，模拟 settings 模块
    支持根据当前用户上下文返回不同的 LLM 配置
    """

    def __init__(self):
        self._cached_settings = None
        self._cache_user_id = None
        # 初始化默认设置
        self._init_default_settings()

    def _init_default_settings(self):
        """初始化默认设置（首次导入时使用）"""
        settings = self._build_settings(user_id=None)
        self._cached_settings = settings
        self._cache_user_id = None

    def _build_settings(self, user_id=None):
        """构建设置对象，所有业务配置从 SystemConfig 动态读取"""
        from backend.api.utils import backend_settings
        from backend.api.core.system_config import SystemConfig

        class Settings:
            pass

        settings = Settings()
        settings.LLM_MODEL = backend_settings.LLM_MODEL
        settings.base_path = backend_settings.base_path
        settings.DEFAULT_SPIDER_NUM = SystemConfig.get_int('search.default_spider_num', 20)
        settings.SERPER_API_KEY = backend_settings.get_serper_api_key(user_id)
        settings.EMBEDDING_CONFIG = backend_settings.get_embedding_config()
        settings.PROCESS_CONFIG = backend_settings.get_process_config()
        settings.PROCESS_IMAGE_TYPE = backend_settings.get_process_image_type()
        settings.EMBEDDING_TYPE = backend_settings.get_embedding_type()
        settings.EMBEDDING_MODEL = backend_settings.get_embedding_model()
        settings.EMBEDDING_DIMENSION = backend_settings.get_embedding_dimension()
        settings.EMBEDDING_TIMEOUT = backend_settings.get_embedding_timeout()
        settings.DEFAULT_IMAGE_EMBEDDING_METHOD = backend_settings.get_image_embedding_method()

        # 添加函数
        settings.get_embedding_type = backend_settings.get_embedding_type
        settings.get_embedding_config = backend_settings.get_embedding_config
        settings.get_embedding_dimension = backend_settings.get_embedding_dimension
        settings.get_embedding_timeout = backend_settings.get_embedding_timeout
        settings.get_embedding_model = backend_settings.get_embedding_model

        return settings

    def clear_cache(self):
        """清除缓存，强制下次访问时重新加载"""
        self._cached_settings = None
        self._cache_user_id = None

    def _get_settings(self):
        """获取当前用户的设置"""
        user_id = get_user_context()

        # 如果缓存存在且用户ID匹配，直接返回
        if self._cached_settings is not None and self._cache_user_id == user_id:
            return self._cached_settings

        # 否则重新构建
        settings = self._build_settings(user_id)
        self._cached_settings = settings
        self._cache_user_id = user_id

        return settings

    def __getattr__(self, name):
        """动态代理属性访问"""
        settings = self._get_settings()
        if hasattr(settings, name):
            return getattr(settings, name)
        return None


# 创建动态设置实例
_dynamic_settings = _DynamicSettings()

# 在导入 searxng_utils 之前，将 settings 替换为动态设置
sys.modules['settings'] = _dynamic_settings

# 现在可以安全导入 searxng_utils
from utils.searxng_utils import Search, llm_task, chat, parse_outline_json

# 导出函数
__all__ = [
    'Search',
    'llm_task',
    'chat',
    'parse_outline_json',
    'set_user_context',  # 新：设置用户上下文
    'get_user_context',  # 新：获取当前用户ID
]
