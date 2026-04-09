# -*- coding: utf-8 -*-
"""
SupaWriter 健康检查路由
提供应用和数据库健康状态检查
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from backend.api.core.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    service: str
    version: str
    timestamp: str
    database: Optional[Dict[str, Any]] = None


class DatabaseHealthStatus(BaseModel):
    """数据库健康状态模型"""
    status: str  # healthy, degraded, unhealthy
    latency_ms: Optional[int] = None
    message: Optional[str] = None


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    基础健康检查接口

    返回应用的基本健康状态，不检查数据库连接。
    """
    return HealthCheckResponse(
        status="healthy",
        service="SupaWriter API",
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/health/database", response_model=DatabaseHealthStatus)
async def database_health_check(session: AsyncSession = Depends(get_db)):
    """
    数据库健康检查接口

    检查数据库连接状态和响应时间。

    Returns:
        DatabaseHealthStatus: 数据库健康状态

    Raises:
        HTTPException: 数据库连接失败时
    """
    start_time = datetime.utcnow()

    try:
        # 执行简单的数据库查询
        result = await session.execute(text("SELECT 1"))
        result.fetchone()

        # 计算延迟
        end_time = datetime.utcnow()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        # 根据延迟确定健康状态
        if latency_ms < 100:
            status = "healthy"
        elif latency_ms < 500:
            status = "degraded"
        else:
            status = "degraded"

        return DatabaseHealthStatus(
            status=status,
            latency_ms=latency_ms,
            message=f"Database response time: {latency_ms}ms"
        )

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )


@router.get("/health/full", response_model=HealthCheckResponse)
async def full_health_check(session: AsyncSession = Depends(get_db)):
    """
    完整健康检查接口

    检查应用和数据库的健康状态。

    Returns:
        HealthCheckResponse: 完整的健康状态信息
    """
    overall_status = "healthy"
    db_info = None

    try:
        # 检查数据库连接
        start_time = datetime.utcnow()
        result = await session.execute(text("SELECT 1"))
        result.fetchone()
        end_time = datetime.utcnow()

        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        db_info = {
            "status": "healthy" if latency_ms < 100 else "degraded",
            "latency_ms": latency_ms,
            "connected": True
        }

        if latency_ms >= 100:
            overall_status = "degraded"

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        overall_status = "unhealthy"
        db_info = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }

    return HealthCheckResponse(
        status=overall_status,
        service="SupaWriter API",
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        database=db_info
    )


@router.get("/health/ready")
async def readiness_check(session: AsyncSession = Depends(get_db)):
    """
    就绪检查接口（Kubernetes Readiness Probe）

    检查服务是否准备好接收请求。
    """
    try:
        # 简单的数据库查询检查
        await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/health/live")
async def liveness_check():
    """
    存活检查接口（Kubernetes Liveness Probe）

    检查服务是否正在运行。
    """
    return {"status": "alive"}
