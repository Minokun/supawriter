"""
SupaWriter 简化版后端 API
仅包含核心功能，不依赖 Streamlit 和 utils 目录
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend.api.config import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 SupaWriter API (Simple) starting up...")
    yield
    logger.info("👋 SupaWriter API (Simple) shutting down...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME + " (Simple)",
    version=settings.APP_VERSION,
    description="SupaWriter 简化版 API - 核心功能",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session 中间件
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET_KEY
)


# ==================== 基础路由 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to SupaWriter API (Simple)",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


# ==================== 导入核心路由 ====================
# 只导入不依赖 utils 的路由

try:
    from backend.api.routes import hotspots
    app.include_router(
        hotspots.router,
        prefix=settings.API_V1_PREFIX,
        tags=["hotspots"]
    )
    logger.info("✓ Hotspots routes loaded")
except Exception as e:
    logger.warning(f"✗ Failed to load hotspots routes: {e}")

try:
    from backend.api.routes import news
    app.include_router(
        news.router,
        prefix=settings.API_V1_PREFIX,
        tags=["news"]
    )
    logger.info("✓ News routes loaded")
except Exception as e:
    logger.warning(f"✗ Failed to load news routes: {e}")

try:
    from backend.api.routes import settings as settings_routes
    app.include_router(
        settings_routes.router,
        prefix=f"{settings.API_V1_PREFIX}/settings",
        tags=["settings"]
    )
    logger.info("✓ Settings routes loaded")
except Exception as e:
    logger.warning(f"✗ Failed to load settings routes: {e}")

try:
    from backend.api.routes import auth_google
    app.include_router(
        auth_google.router,
        prefix=f"{settings.API_V1_PREFIX}/auth",
        tags=["auth"]
    )
    logger.info("✓ Google auth routes loaded")
except Exception as e:
    logger.warning(f"✗ Failed to load Google auth routes: {e}")


# ==================== 热点 API Mock ====================
# 如果热点路由加载失败，提供基础的 mock 数据

@app.get(f"{settings.API_V1_PREFIX}/hotspots/sources")
async def get_hotspot_sources_fallback():
    """获取热点源列表（备用）"""
    return {
        "sources": [
            {"id": "baidu", "name": "百度热搜", "enabled": True},
            {"id": "weibo", "name": "微博热搜", "enabled": True},
            {"id": "zhihu", "name": "知乎热榜", "enabled": True},
            {"id": "toutiao", "name": "今日头条", "enabled": True}
        ]
    }


@app.get(f"{settings.API_V1_PREFIX}/hotspots/")
async def get_hotspots_fallback(source: str = "baidu"):
    """获取热点数据（备用）"""
    return {
        "source": source,
        "update_time": "2026-01-30T15:00:00",
        "hotspots": [
            {
                "rank": 1,
                "title": "示例热点标题 1",
                "url": "https://example.com/1",
                "heat": "1000万"
            },
            {
                "rank": 2,
                "title": "示例热点标题 2",
                "url": "https://example.com/2",
                "heat": "800万"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
