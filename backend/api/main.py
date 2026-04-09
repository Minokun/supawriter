# -*- coding: utf-8 -*-
"""
SupaWriter FastAPI Backend - Updated with full middleware integration
统一后端服务，为创作工具和社区网站提供 API
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from prometheus_client import make_asgi_app
import logging
import os
import secrets

# Import configuration and managers
from backend.api.core.config import get_settings
from backend.api.core.redis_manager import get_redis_manager
from backend.api.core.monitoring import get_metrics_collector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    
    # 启动时执行
    logger.info(f"Starting {settings.app_name} v{settings.app_version}...")
    logger.info(f"Environment: {settings.environment}")

    # 初始化数据库连接池
    try:
        from backend.api.core.database import init_db_pool
        await init_db_pool()
        logger.info("✓ Database connection initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")

    # 初始化 Redis 连接
    if settings.redis:
        try:
            redis_manager = get_redis_manager()
            await redis_manager.connect()
            logger.info("✓ Redis connection initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Redis: {e}")

    # 初始化监控
    if settings.monitoring.enabled:
        logger.info("✓ Monitoring enabled")

    # 预加载系统配置到内存缓存
    try:
        from backend.api.core.system_config import SystemConfig
        SystemConfig.reload()
        logger.info("✓ SystemConfig preloaded")
    except Exception as e:
        logger.warning(f"⚠ Failed to preload SystemConfig: {e}")

    yield

    # 关闭时执行
    logger.info(f"Shutting down {settings.app_name}...")

    # 关闭 Redis 连接
    try:
        redis_manager = get_redis_manager()
        await redis_manager.disconnect()
        logger.info("✓ Redis connection closed")
    except Exception as e:
        logger.error(f"✗ Error closing Redis: {e}")

    # 关闭数据库连接池
    try:
        from backend.api.core.database import close_db_pool
        await close_db_pool()
        logger.info("✓ Database connection closed")
    except Exception as e:
        logger.error(f"✗ Error closing database: {e}")


# 创建 FastAPI 应用
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="超能写手统一后端 API - ORM Refactored",
    version=settings.app_version,
    lifespan=lifespan
)

# SessionMiddleware - OAuth 需要
secret_key = settings.secret_key
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# ===== 全局中间件集成 =====
# 注意：中间件的添加顺序很重要
# 1. AuditLogMiddleware - 最先执行，记录所有请求
# 2. RateLimitMiddleware - 短期速率限制
# 3. QuotaCheckMiddleware - 长期配额检查（在路由级别应用）

# 导入中间件
from backend.api.middleware.audit_log import AuditLogMiddleware
from backend.api.middleware.rate_limit import RateLimitMiddleware
from backend.api.middleware.rate_limit_redis import RateLimiterRedis
from backend.api.services.audit import AuditService
from backend.api.services.quota import QuotaService
from backend.api.core.dependencies import get_db

# 创建全局服务实例（用于中间件）
# 注意：使用 async context manager 确保 session 在中间件 dispatch 期间保持活跃
from contextlib import asynccontextmanager as _asynccontextmanager

class GlobalServices:
    """全局服务容器"""
    
    @staticmethod
    @_asynccontextmanager
    async def get_audit_service():
        """获取审计服务（上下文管理器，确保 session 生命周期正确）"""
        from backend.api.db.session import get_async_db_session
        
        async with get_async_db_session() as session:
            from backend.api.repositories.audit import AuditLogRepository
            audit_repo = AuditLogRepository(session)
            yield AuditService(session, audit_repo)
    
    @staticmethod
    @_asynccontextmanager
    async def get_quota_service():
        """获取配额服务（上下文管理器，确保 session 生命周期正确）"""
        from backend.api.db.session import get_async_db_session
        
        async with get_async_db_session() as session:
            from backend.api.repositories.quota import QuotaRepository
            quota_repo = QuotaRepository(session)
            yield QuotaService(session, quota_repo)


# 添加审计日志中间件
if settings.audit.enabled:
    try:
        # 创建审计服务工厂（返回 async context manager）
        def audit_service_factory():
            return GlobalServices.get_audit_service()
        
        app.add_middleware(
            AuditLogMiddleware,
            audit_service_factory=audit_service_factory,
            log_request_body=settings.audit.log_request_body,
            log_response_body=settings.audit.log_response_body,
            sensitive_fields=settings.audit.sensitive_fields
        )
        logger.info("✓ Audit log middleware enabled")
    except Exception as e:
        logger.error(f"✗ Failed to add audit middleware: {e}")

# 添加限流中间件
if settings.rate_limit.enabled:
    try:
        # 创建限流器（Redis 在 startup 事件中才连接，此处先用内存限流器）
        from backend.api.middleware.rate_limit import RateLimiterMemory
        rate_limiter = RateLimiterMemory()
        if settings.rate_limit.use_redis:
            logger.info("⚠ Rate limiter: using memory fallback (Redis connects at startup)")
        else:
            logger.info("ℹ Using memory rate limiter")
        
        # 创建配额服务工厂（返回 async context manager）
        def quota_service_factory():
            return GlobalServices.get_quota_service()
        
        app.add_middleware(
            RateLimitMiddleware,
            quota_service_factory=quota_service_factory,
            rate_limiter=rate_limiter,
            requests_per_minute=settings.rate_limit.requests_per_minute,
            public_endpoints=["/api/v1/auth/login", "/api/v1/auth/register"],
            exclude_paths=settings.rate_limit.exclude_paths
        )
        logger.info("✓ Rate limit middleware enabled")
    except Exception as e:
        logger.error(f"✗ Failed to add rate limit middleware: {e}")


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # 记录到监控
    metrics = get_metrics_collector()
    metrics.record_request(
        method=request.method,
        endpoint=request.url.path,
        status=500,
        duration=0
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred"
        }
    )


# 导入并注册路由
from backend.api.routes import (
    auth, auth_exchange, articles, chat,
    hotspots, hotspots_v2, news, websocket, settings as settings_route,
    articles_enhanced, health, admin, tweet_topics,
    alerts, dashboard, batch, agent, pricing, subscription
)

# 健康检查路由（不使用 /api/v1 前缀，用于容器编排）
app.include_router(health.router, tags=["health"])

# 认证路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(auth_exchange.router, prefix="/api/v1/auth", tags=["auth"])

# 文章路由（只使用 articles_enhanced，包含所有文章相关功能）
app.include_router(articles_enhanced.router, prefix="/api/v1/articles", tags=["articles"])

# AI 助手路由
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

# 热点路由
app.include_router(hotspots.router, prefix="/api/v1/hotspots", tags=["hotspots"])

# 热点路由 V2 (newsnow API)
app.include_router(hotspots_v2.router, prefix="/api/v1/hotspots/v2", tags=["hotspots-v2"])

# 新闻路由
app.include_router(news.router, prefix="/api/v1/news", tags=["news"])

# WebSocket 路由
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])

# 设置路由
app.include_router(settings_route.router, prefix="/api/v1/settings", tags=["settings"])

# 管理路由（仅超级管理员）
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# 推文选题路由
app.include_router(tweet_topics.router, prefix="/api/v1/tweet-topics", tags=["tweet-topics"])

# Sprint 6: 预警和看板路由
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])

# Sprint 7: 批量生成和写作Agent路由
app.include_router(batch.router, prefix="/api/v1", tags=["batch"])
app.include_router(agent.router, prefix="/api/v1", tags=["agents"])

# Sprint 8: 付费体系路由
app.include_router(pricing.router, prefix="/api/v1", tags=["pricing"])
app.include_router(subscription.router, prefix="/api/v1", tags=["subscription"])


# Prometheus metrics endpoint
if settings.monitoring.prometheus_enabled:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    logger.info("✓ Prometheus metrics endpoint enabled at /metrics")


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "metrics": "/metrics" if settings.monitoring.prometheus_enabled else None,
        "endpoints": {
            "auth": "/api/v1/auth",
            "articles": "/api/v1/articles",
            "chat": "/api/v1/chat",
            "hotspots": "/api/v1/hotspots",
            "news": "/api/v1/news",
            "websocket": "/api/v1/ws",
            "settings": "/api/v1/settings"
        },
        "features": {
            "rate_limiting": settings.rate_limit.enabled,
            "quota_management": settings.quota.enabled,
            "audit_logging": settings.audit.enabled,
            "caching": settings.cache.enabled,
            "monitoring": settings.monitoring.enabled
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
