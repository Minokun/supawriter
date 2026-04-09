# -*- coding: utf-8 -*-
"""
Backend LLM Provider Configuration
分离自 streamlit settings，供 backend API 和 worker 使用
"""

import os
from typing import Dict, Optional, List


def get_llm_providers() -> Dict[str, Dict[str, str]]:
    """
    获取 LLM 提供商配置

    从环境变量读取配置，格式为：
    - DEEPSEEK_MODEL, DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY
    - OPENAI_MODEL, OPENAI_BASE_URL, OPENAI_API_KEY
    等等
    """
    providers = {}

    # DeepSeek (主要提供商)
    deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if deepseek_api_key:
        providers['deepseek'] = {
            'model': deepseek_model,
            'base_url': deepseek_base_url,
            'api_key': deepseek_api_key
        }

    # OpenAI
    openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if openai_api_key:
        providers['openai'] = {
            'model': openai_model,
            'base_url': openai_base_url,
            'api_key': openai_api_key
        }

    # Qwen (通义千问)
    qwen_model = os.getenv("QWEN_MODEL", "qwen-plus")
    qwen_base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    qwen_api_key = os.getenv("QWEN_API_KEY", "")
    if qwen_api_key:
        providers['qwen'] = {
            'model': qwen_model,
            'base_url': qwen_base_url,
            'api_key': qwen_api_key
        }

    # GLM (智谱)
    glm_model = os.getenv("GLM_MODEL", "glm-4-flash")
    glm_base_url = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    glm_api_key = os.getenv("GLM_API_KEY", "")
    if glm_api_key:
        providers['glm'] = {
            'model': glm_model,
            'base_url': glm_base_url,
            'api_key': glm_api_key
        }

    return providers


def get_default_provider() -> str:
    """获取默认 LLM 提供商"""
    providers = get_llm_providers()
    # 优先使用 deepseek，其次第一个可用的
    if 'deepseek' in providers:
        return 'deepseek'
    return list(providers.keys())[0] if providers else 'deepseek'


# LLM 模型配置
LLM_MODEL = get_llm_providers()

# 默认提供商
DEFAULT_LLM_PROVIDER = get_default_provider()

# ============================================================================
# 以下业务配置统一从 system_settings 表读取（通过 backend_settings）
# 保留模块级变量以兼容旧导入，但推荐使用 backend_settings 中的函数
# ============================================================================

def _get_system_config():
    """延迟导入 SystemConfig"""
    from backend.api.core.system_config import SystemConfig
    return SystemConfig

# 文章生成默认配置
try:
    DEFAULT_SPIDER_NUM = _get_system_config().get_int('search.default_spider_num', 20)
    DEFAULT_ENABLE_IMAGES = _get_system_config().get_bool('article.default_enable_images', True)
    SERPER_API_KEY = _get_system_config().get('search.serper_api_key') or _get_system_config().get('serper.api_key')
    EMBEDDING_TYPE = _get_system_config().get('embedding.default_provider', 'gitee')
    EMBEDDING_MODEL = _get_system_config().get('embedding.model', 'Qwen3-VL-Embedding-8B')
    EMBEDDING_DIMENSION = _get_system_config().get_int('embedding.dimension', 2048)
    EMBEDDING_TIMEOUT = _get_system_config().get_int('embedding.timeout', 10)
    PROCESS_IMAGE_TYPE = _get_system_config().get('article.process_image_type', 'glm')
    PROCESS_CONFIG = _get_system_config().get_json('article.process_config', {
        "qwen": {"model": "qwen-vl-plus-2025-01-25"},
        "glm": {"model": "glm-4.5v"}
    })
except Exception:
    DEFAULT_SPIDER_NUM = 20
    DEFAULT_ENABLE_IMAGES = True
    SERPER_API_KEY = None
    EMBEDDING_TYPE = 'gitee'
    EMBEDDING_MODEL = 'Qwen3-VL-Embedding-8B'
    EMBEDDING_DIMENSION = 2048
    EMBEDDING_TIMEOUT = 10
    PROCESS_IMAGE_TYPE = 'glm'
    PROCESS_CONFIG = {
        "qwen": {"model": "qwen-vl-plus-2025-01-25"},
        "glm": {"model": "glm-4.5v"}
    }

# Embedding API 配置 - 委托给 backend_settings
def get_embedding_config() -> Dict:
    """获取 embedding 配置（从 system_settings 读取）"""
    from backend.api.utils.backend_settings import get_embedding_config as _get_ec
    return _get_ec()

EMBEDDING_CONFIG = {}
