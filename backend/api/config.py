# -*- coding: utf-8 -*-
"""
SupaWriter API 配置管理
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict
from pydantic_settings import BaseSettings


# 添加项目根目录到 Python 路径
def get_project_root() -> Path:
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


# 确保 backend 目录在路径中
backend_dir = get_project_root() / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "SupaWriter API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 数据库配置
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # JWT 配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # OAuth 配置
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    WECHAT_APPID: Optional[str] = os.getenv("WECHAT_APPID")
    WECHAT_SECRET: Optional[str] = os.getenv("WECHAT_SECRET")

    # 前端 URL 配置
    CREATOR_URL: str = os.getenv("CREATOR_URL", "http://localhost:3000")
    COMMUNITY_URL: str = os.getenv("COMMUNITY_URL", "http://localhost:3001")

    # API 配置
    API_V1_PREFIX: str = "/api/v1"

    # CORS 配置
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8501",  # Streamlit
    ]

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: Path = get_project_root() / "uploads"

    # WebSocket 配置
    WS_HEARTBEAT_INTERVAL: int = 30  # 心跳间隔（秒）

    # Redis 配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

    # Article Worker 配置
    ARTICLE_QUEUE_NAME: str = "arq:queue"

    # 加密密钥（用于 API 密钥加密）
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

    @property
    def REDIS_URL(self) -> str:
        """获取 Redis 连接 URL"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = get_project_root() / "deployment" / ".env"
        case_sensitive = True
        extra = "ignore"  # 忽略 .env 中的额外字段


# 创建全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例（用于依赖注入）"""
    return settings


# 确保上传目录存在
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# LLM 配置 - 从 backend.api.config.llm 导入
# ============================================================================
# 这些配置用于 article worker 和文章生成功能
# 在导入时延迟加载，避免循环依赖
_llm_config = None


def get_llm_config():
    """获取 LLM 配置（延迟加载）"""
    global _llm_config
    if _llm_config is None:
        from backend.api.config.llm import (
            LLM_MODEL,
            DEFAULT_LLM_PROVIDER,
            DEFAULT_SPIDER_NUM,
            DEFAULT_ENABLE_IMAGES,
            SERPER_API_KEY,
            EMBEDDING_CONFIG,
            PROCESS_CONFIG
        )
        _llm_config = {
            'LLM_MODEL': LLM_MODEL,
            'DEFAULT_LLM_PROVIDER': DEFAULT_LLM_PROVIDER,
            'DEFAULT_SPIDER_NUM': DEFAULT_SPIDER_NUM,
            'DEFAULT_ENABLE_IMAGES': DEFAULT_ENABLE_IMAGES,
            'SERPER_API_KEY': SERPER_API_KEY,
            'EMBEDDING_CONFIG': EMBEDDING_CONFIG,
            'PROCESS_CONFIG': PROCESS_CONFIG
        }
    return _llm_config


# 导出 LLM 配置的快捷访问
@property
def LLM_MODEL(self) -> Dict:
    """LLM 模型配置"""
    return get_llm_config()['LLM_MODEL']


@property
def DEFAULT_LLM_PROVIDER(self) -> str:
    """默认 LLM 提供商"""
    return get_llm_config()['DEFAULT_LLM_PROVIDER']


@property
def DEFAULT_SPIDER_NUM(self) -> int:
    """默认爬取文章数量"""
    return get_llm_config()['DEFAULT_SPIDER_NUM']


@property
def DEFAULT_ENABLE_IMAGES(self) -> bool:
    """默认是否启用图片"""
    return get_llm_config()['DEFAULT_ENABLE_IMAGES']


@property
def SERPER_API_KEY(self) -> Optional[str]:
    """Serper API Key"""
    return get_llm_config()['SERPER_API_KEY']


@property
def EMBEDDING_CONFIG(self) -> Dict:
    """Embedding 配置"""
    return get_llm_config()['EMBEDDING_CONFIG']


@property
def PROCESS_CONFIG(self) -> Dict:
    """图片处理配置"""
    return get_llm_config()['PROCESS_CONFIG']


# 动态添加属性到 Settings 类
Settings.LLM_MODEL = LLM_MODEL
Settings.DEFAULT_LLM_PROVIDER = DEFAULT_LLM_PROVIDER
Settings.DEFAULT_SPIDER_NUM = DEFAULT_SPIDER_NUM
Settings.DEFAULT_ENABLE_IMAGES = DEFAULT_ENABLE_IMAGES
Settings.SERPER_API_KEY = SERPER_API_KEY
Settings.EMBEDDING_CONFIG = EMBEDDING_CONFIG
Settings.PROCESS_CONFIG = PROCESS_CONFIG
