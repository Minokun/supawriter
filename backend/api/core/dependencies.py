# -*- coding: utf-8 -*-
"""
SupaWriter API 依赖注入
提供可复用的依赖项（如认证用户、数据库连接等）
"""

from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from backend.api.core.security import verify_token
from backend.api.core.websocket import manager
from backend.api.config import settings
from backend.api.db.session import get_async_db_session
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[int]:
    """
    获取当前用户 ID（可选）

    如果提供了 token 则验证，否则返回 None

    Returns:
        用户 ID，如果 token 无效则返回 None
    """
    if credentials is None:
        return None

    token = credentials.credentials
    user_id = verify_token(token)

    if user_id is None:
        return None

    return user_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    获取当前用户 ID（必需）

    需要提供有效的 token，否则抛出 401 异常

    Returns:
        用户 ID

    Raises:
        HTTPException: 如果 token 无效
    """
    logger.info(f"get_current_user called, credentials: {credentials is not None}")
    
    if credentials is None:
        logger.warning("No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    logger.info(f"Token received (first 20 chars): {token[:20]}...")
    
    user_id = verify_token(token)
    logger.info(f"Token verification result: user_id={user_id}")

    if user_id is None:
        logger.warning("Token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"User authenticated: user_id={user_id}")
    return user_id


async def get_ws_user(websocket: WebSocket) -> Optional[int]:
    """
    从 WebSocket 连接获取用户 ID

    通过查询参数获取 token 并验证

    Args:
        websocket: WebSocket 连接

    Returns:
        用户 ID，如果 token 无效则返回 None
    """
    # 从查询参数获取 token
    token = websocket.query_params.get("token")

    if token is None:
        return None

    user_id = verify_token(token)
    return user_id


async def require_ws_user(websocket: WebSocket) -> int:
    """
    从 WebSocket 连接获取用户 ID（必需）

    如果 token 无效则关闭连接

    Args:
        websocket: WebSocket 连接

    Returns:
        用户 ID

    Raises:
        WebSocketDisconnect: 如果 token 无效
    """
    from fastapi import WebSocketDisconnect

    user_id = await get_ws_user(websocket)

    if user_id is None:
        await websocket.close(code=1008, reason="Invalid token")
        raise WebSocketDisconnect(code=1008, reason="Invalid token")

    return user_id


class RateLimiter:
    """
    简单的速率限制器

    用于防止 API 滥用
    """

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        检查是否允许请求

        Args:
            identifier: 标识符（通常是 user_id 或 IP）

        Returns:
            是否允许请求
        """
        import time

        now = int(time.time())

        # 清理过期记录
        self._cleanup(now)

        # 获取或创建用户请求记录
        if identifier not in self.requests:
            self.requests[identifier] = []

        # 添加当前请求时间戳
        self.requests[identifier].append(now)

        # 检查是否超过限制
        request_count = len(self.requests[identifier])
        return request_count <= self.max_requests

    def _cleanup(self, now: int):
        """清理过期的请求记录"""
        expired_identifiers = []

        for identifier, timestamps in self.requests.items():
            # 移除超过时间窗口的记录
            self.requests[identifier] = [
                ts for ts in timestamps
                if now - ts < self.time_window
            ]

            # 如果没有记录了，标记为待删除
            if not self.requests[identifier]:
                expired_identifiers.append(identifier)

        # 删除空记录
        for identifier in expired_identifiers:
            del self.requests[identifier]


# 创建速率限制器实例
rate_limiter = RateLimiter(max_requests=100, time_window=60)


async def check_rate_limit(user_id: int):
    """
    检查速率限制

    Args:
        user_id: 用户 ID

    Raises:
        HTTPException: 如果超过速率限制
    """
    if not rate_limiter.is_allowed(str(user_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )


def paginate(page: int = 1, page_size: int = 20) -> tuple:
    """
    分页参数处理

    Args:
        page: 页码（从 1 开始）
        page_size: 每页数量

    Returns:
        (offset, limit) 元组
    """
    # 限制最大 page_size
    page_size = min(page_size, 100)

    # 计算 offset
    offset = (page - 1) * page_size

    return offset, page_size


async def get_db() -> AsyncSession:
    """
    获取数据库 session（依赖注入）

    Yields:
        AsyncSession: 数据库 session
    """
    async with get_async_db_session() as session:
        yield session


# ============ 权限检查依赖 ============

from backend.api.services.tier_service import TierService
from utils.database import Database


async def require_admin(current_user_id: int = Depends(get_current_user)) -> int:
    """要求超级管理员权限"""
    if not TierService.is_superuser(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
    return current_user_id


async def get_user_tier(current_user_id: int = Depends(get_current_user)) -> str:
    """获取当前用户的会员等级"""
    return TierService.get_user_tier(current_user_id)


async def get_user_info_with_tier(current_user_id: int = Depends(get_current_user)) -> dict:
    """获取包含会员等级的用户信息"""
    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT id, username, email, display_name, membership_tier
            FROM users WHERE id = %s
        """, (current_user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        return {
            "id": row['id'],
            "username": row['username'],
            "email": row['email'],
            "display_name": row['display_name'],
            "membership_tier": row['membership_tier'],
            "is_admin": TierService.is_superuser(current_user_id)
        }
