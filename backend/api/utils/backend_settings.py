# -*- coding: utf-8 -*-
"""
Backend Settings Shim
为 backend worker 提供与根目录 settings.py 兼容的接口
不依赖 streamlit

配置来源：
1. LLM_MODEL: 从数据库 llm_providers 表读取（用户级别配置）
2. 所有业务配置: 从 system_settings 表读取（通过 SystemConfig）
3. .env: 仅基础设施配置（DB, Redis, JWT 等）
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any

# 添加 backend 到路径
backend_root = Path(__file__).parent.parent.parent.parent
backend_dir = backend_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# 添加项目根目录到路径（用于导入 utils 模块）
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

base_path = str(backend_root)

logger = logging.getLogger(__name__)


def _get_system_config():
    """延迟导入 SystemConfig 避免循环依赖"""
    from backend.api.core.system_config import SystemConfig
    return SystemConfig


# ============================================================================
# 从数据库读取 LLM 配置
# ============================================================================

def get_user_llm_config(user_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """
    从数据库获取用户的 LLM 提供商配置

    如果用户没有配置提供商，则使用管理员（user_id=1）的配置作为默认值

    Args:
        user_id: 用户ID，如果为 None 则尝试获取第一个可用用户的配置

    Returns:
        LLM_MODEL 格式的字典: {
            'deepseek': {'model': 'deepseek-chat', 'base_url': '...', 'api_key': '...'},
            ...
        }
    """
    try:
        from utils.database import Database
        from backend.api.core.encryption import encryption_manager

        # 如果没有提供 user_id，尝试使用默认用户（第一个用户）
        if user_id is None:
            with Database.get_cursor() as cursor:
                cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
                row = cursor.fetchone()
                if row:
                    user_id = row['id']
                else:
                    return {}

        # 从数据库获取用户的 LLM 提供商配置
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT provider_id, provider_name, base_url, api_key_encrypted, models, enabled
                FROM llm_providers
                WHERE user_id = %s AND enabled = TRUE
                ORDER BY provider_id
            """, (user_id,))

            rows = cursor.fetchall()
            llm_model = {}

            for row in rows:
                provider_id = row['provider_id']
                # 解密 API key
                api_key = ""
                if row['api_key_encrypted']:
                    try:
                        api_key = encryption_manager.decrypt(row['api_key_encrypted'])
                    except Exception as e:
                        print(f"Failed to decrypt API key for {provider_id}: {e}")

                # 获取模型（从 models JSONB 或默认值）
                models = row['models'] if row['models'] else []

                llm_model[provider_id] = {
                    'model': models[0] if models else row['provider_name'],  # 使用第一个模型或提供商名称
                    'base_url': row['base_url'],
                    'api_key': api_key
                }

            # 如果用户没有配置提供商，使用管理员（user_id=1）的配置作为默认值
            if not llm_model and user_id != 1:
                print(f"User {user_id} has no LLM providers configured, falling back to admin config")
                return get_user_llm_config(1)

            return llm_model

    except Exception as e:
        print(f"Error loading LLM config from database: {e}")
        return {}


def get_user_llm_config_cached(user_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """
    获取用户 LLM 配置（带缓存）

    Args:
        user_id: 用户ID

    Returns:
        LLM_MODEL 格式的字典
    """
    # 简单缓存：使用全局变量存储已加载的配置
    if not hasattr(get_user_llm_config_cached, '_cache'):
        get_user_llm_config_cached._cache = {}
        get_user_llm_config_cached._cache_user_id = None

    # 如果 user_id 变化，清空缓存
    if get_user_llm_config_cached._cache_user_id != user_id:
        get_user_llm_config_cached._cache = None
        get_user_llm_config_cached._cache_user_id = user_id

    if get_user_llm_config_cached._cache is None:
        get_user_llm_config_cached._cache = get_user_llm_config(user_id)

    return get_user_llm_config_cached._cache or {}


# ============================================================================
# 系统配置读取（统一通过 SystemConfig）
# ============================================================================

# 动态属性 - 每次访问从 SystemConfig 读取最新值
@property
def _default_spider_num():
    return _get_system_config().get_int('search.default_spider_num', 20)

# 模块级兼容变量（首次导入时求值，后续通过函数获取最新值）
DEFAULT_SPIDER_NUM = 20  # 兼容旧代码，推荐使用 get_default_spider_num()

def get_default_spider_num() -> int:
    """获取默认搜索数量（从 system_settings 动态读取）"""
    return _get_system_config().get_int('search.default_spider_num', 20)


def get_system_setting(key: str, default: Any = None) -> Any:
    """
    从 system_settings 表获取系统配置（兼容旧接口）

    推荐直接使用 SystemConfig.get(key, default)
    """
    return _get_system_config().get(key, default)


def get_qiniu_config() -> Dict[str, str]:
    """获取七牛云配置"""
    sc = _get_system_config()
    return {
        'domain': sc.get('qiniu.domain', ''),
        'folder': sc.get('qiniu.folder', ''),
        'access_key': sc.get('qiniu.access_key', ''),
        'secret_key': sc.get('qiniu.secret_key', ''),
        'region': sc.get('qiniu.region', 'z2')
    }


def get_serper_api_key(user_id: Optional[int] = None) -> Optional[str]:
    """
    从数据库获取 Serper API Key

    优先读取新 key (search.serper_api_key)，兼容旧 key (serper.api_key)
    user_id 参数保留以保持向后兼容
    """
    sc = _get_system_config()
    key = sc.get('search.serper_api_key')
    if key:
        return key
    # 兼容旧 key
    return sc.get('serper.api_key')


# ============================================================================
# Embedding 配置 - 从 system_settings 表读取
# ============================================================================

def get_embedding_config() -> Dict[str, Dict[str, Any]]:
    """
    获取 embedding API 配置（从 system_settings 表读取）

    Returns:
        包含各提供商配置的字典，格式与 utils/embedding_utils.py 兼容
    """
    sc = _get_system_config()
    embedding_model = sc.get('embedding.model', 'Qwen3-VL-Embedding-8B')
    embedding_timeout = sc.get_int('embedding.timeout', 10)

    # Jina 配置
    jina_base_url = sc.get('embedding.jina.base_url', '')
    jina_api_key = sc.get('embedding.jina.api_key', '')

    # Gitee AI 配置
    gitee_base_url = sc.get('embedding.gitee.base_url', 'https://ai.gitee.com/v1')
    gitee_api_key = sc.get('embedding.gitee.api_key', '')

    return {
        'gitee': {
            'model': embedding_model,
            'host': gitee_base_url + '/embeddings',
            'api_key': gitee_api_key,
            'timeout': embedding_timeout
        },
        'jina': {
            'model': embedding_model,
            'host': jina_base_url + '/embeddings' if jina_base_url else '',
            'api_key': jina_api_key,
            'timeout': embedding_timeout
        },
        'xinference': {
            'model': embedding_model,
            'host': os.getenv("XINFERENCE_BASE_URL", "http://10.10.10.90:7009/v1") + '/embeddings',
            'api_key': os.getenv("XINFERENCE_API_KEY", ""),
            'timeout': embedding_timeout
        },
        'dashscope': {
            'model': embedding_model,
            'host': os.getenv("DASHSCOPE_BASE_URL", "") + '/embeddings',
            'api_key': os.getenv("DASHSCOPE_API_KEY", ""),
            'timeout': embedding_timeout
        },
        'glm': {
            'model': embedding_model,
            'host': os.getenv("GLM_BASE_URL", "") + '/embeddings',
            'api_key': os.getenv("GLM_API_KEY", ""),
            'timeout': embedding_timeout
        }
    }


def get_user_embedding_config(user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    获取 embedding 配置（优先使用系统配置）

    Args:
        user_id: 用户ID（当前未使用，保留用于扩展）
    """
    sc = _get_system_config()
    embedding_type = sc.get('embedding.default_provider', 'gitee')
    embedding_model = sc.get('embedding.model', 'Qwen3-VL-Embedding-8B')
    dimension = sc.get_int('embedding.dimension', 2048)
    timeout = sc.get_int('embedding.timeout', 10)

    return {
        'type': embedding_type,
        'model': embedding_model,
        'dimension': dimension,
        'timeout': timeout
    }


# 兼容旧代码的动态函数
def get_embedding_type() -> str:
    """获取 embedding 类型"""
    return _get_system_config().get('embedding.default_provider', 'gitee')

def get_embedding_model() -> str:
    """获取 embedding 模型"""
    return _get_system_config().get('embedding.model', 'Qwen3-VL-Embedding-8B')

def get_embedding_dimension() -> int:
    """获取 embedding 维度"""
    return _get_system_config().get_int('embedding.dimension', 2048)

def get_embedding_timeout() -> int:
    """获取 embedding 超时时间"""
    return _get_system_config().get_int('embedding.timeout', 10)


# 兼容旧代码的模块级变量（首次导入时求值）
# 推荐使用上面的函数获取最新值
try:
    EMBEDDING_TYPE = get_embedding_type()
    EMBEDDING_MODEL = get_embedding_model()
    EMBEDDING_DIMENSION = get_embedding_dimension()
    EMBEDDING_TIMEOUT = get_embedding_timeout()
    EMBEDDING_CONFIG = get_embedding_config()
except Exception:
    # 数据库未就绪时的兜底默认值
    EMBEDDING_TYPE = 'gitee'
    EMBEDDING_MODEL = 'Qwen3-VL-Embedding-8B'
    EMBEDDING_DIMENSION = 2048
    EMBEDDING_TIMEOUT = 10
    EMBEDDING_CONFIG = {}


# 图片处理配置 - 从 system_settings 读取
def get_process_image_type() -> str:
    """获取图片处理模型类型"""
    return _get_system_config().get('article.process_image_type', 'glm')

def get_process_config() -> Dict[str, Any]:
    """获取图片处理模型配置"""
    return _get_system_config().get_json('article.process_config', {
        "qwen": {"model": "qwen-vl-plus-2025-01-25"},
        "glm": {"model": "glm-4.5v"}
    })

# 兼容旧代码的模块级变量
try:
    PROCESS_IMAGE_TYPE = get_process_image_type()
    PROCESS_CONFIG = get_process_config()
except Exception:
    PROCESS_IMAGE_TYPE = 'glm'
    PROCESS_CONFIG = {
        "qwen": {"model": "qwen-vl-plus-2025-01-25"},
        "glm": {"model": "glm-4.5v"}
    }

# 图片嵌入方式
def get_image_embedding_method() -> str:
    """获取图片嵌入方式"""
    return _get_system_config().get('article.image_embedding_method', 'direct_embedding')

DEFAULT_IMAGE_EMBEDDING_METHOD = 'direct_embedding'  # 兼容旧代码


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'base_path',
    'get_user_llm_config',
    'get_user_llm_config_cached',
    'get_user_embedding_config',
    'get_serper_api_key',
    'get_default_spider_num',
    'get_system_setting',
    'get_qiniu_config',
    'get_embedding_config',
    'get_embedding_type',
    'get_embedding_model',
    'get_embedding_dimension',
    'get_embedding_timeout',
    'get_process_image_type',
    'get_process_config',
    'get_image_embedding_method',
    'DEFAULT_SPIDER_NUM',
    'EMBEDDING_CONFIG',
    'PROCESS_CONFIG',
    'PROCESS_IMAGE_TYPE',
    'EMBEDDING_TYPE',
    'EMBEDDING_MODEL',
    'EMBEDDING_DIMENSION',
    'EMBEDDING_TIMEOUT',
    'DEFAULT_IMAGE_EMBEDDING_METHOD',
]


# ============================================================================
# 向后兼容：支持从 settings 导入 LLM_MODEL（使用默认用户）
# ============================================================================

class _LLMModelProxy:
    """
    LLM_MODEL 代理类，支持动态获取配置

    用法：
    LLM_MODEL = _LLMModelProxy()
    model_config = LLM_MODEL.get(user_id)

    注意：为了支持动态配置（如用户上下文变化），此代理类每次访问都会重新获取配置
    """

    def __init__(self):
        # 简单缓存：只在短时间内有效，避免频繁数据库查询
        self._cache = {}
        self._cache_user_id = None
        self._cache_time = 0
        self._cache_ttl = 5  # 缓存5秒

    def _is_cache_valid(self) -> bool:
        """检查缓存是否仍然有效"""
        import time
        return time.time() - self._cache_time < self._cache_ttl

    def _refresh_cache(self, user_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """刷新缓存"""
        import time

        # 如果没有提供 user_id，尝试从 searxng_compat 获取当前用户上下文
        if user_id is None:
            try:
                from backend.api.utils import searxng_compat
                user_id = searxng_compat.get_user_context()
            except ImportError:
                pass

        self._cache = get_user_llm_config(user_id)
        self._cache_user_id = user_id
        self._cache_time = time.time()
        return self._cache

    def get(self, user_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """获取指定用户的 LLM 配置"""
        if not self._is_cache_valid() or self._cache_user_id != user_id:
            self._refresh_cache(user_id)
        return self._cache

    def keys(self):
        """返回可用的提供商列表"""
        if not self._is_cache_valid():
            self._refresh_cache()
        return list(self._cache.keys())

    def __getitem__(self, key):
        """支持字典式访问"""
        if not self._is_cache_valid():
            self._refresh_cache()
        return self._cache[key]

    def __contains__(self, key):
        """支持 'in' 操作符"""
        if not self._is_cache_valid():
            self._refresh_cache()
        return key in self._cache

    def items(self):
        """支持 .items() 方法"""
        if not self._is_cache_valid():
            self._refresh_cache()
        return self._cache.items()

    def __repr__(self):
        return f"<_LLMModelProxy: {list(self.keys())}>"


# 创建 LLM_MODEL 代理实例
LLM_MODEL = _LLMModelProxy()
