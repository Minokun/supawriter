# -*- coding: utf-8 -*-
"""
SupaWriter WebSocket 路由
处理实时通信、进度推送、流式响应
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import logging
import asyncio

from backend.api.core.websocket import manager
from backend.api.core.dependencies import require_ws_user
from backend.api.config import settings


logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT token")
):
    """
    WebSocket 连接端点

    用于实时通信：
    - 文章生成进度推送
    - AI 助手流式响应
    - 队列状态更新

    Args:
        websocket: WebSocket 连接
        token: JWT token（通过查询参数传递）
    """
    # 验证 token
    from backend.api.core.security import verify_token

    if token is None:
        await websocket.close(code=1008, reason="Missing token")
        return

    user_id = verify_token(token)
    if user_id is None:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # 连接 WebSocket
    await manager.connect(str(user_id), websocket)

    try:
        # 启动心跳检测
        heartbeat_task = asyncio.create_task(
            websocket_heartbeat(websocket, str(user_id))
        )

        # 消息循环
        while True:
            data = await websocket.receive_text()

            # 处理客户端消息
            try:
                import json
                message = json.loads(data)

                # 处理 pong 响应
                if message.get("type") == "pong":
                    continue

                # 处理其他消息类型
                await handle_client_message(str(user_id), message)

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from user {user_id}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # 清理
        await manager.disconnect(str(user_id))
        heartbeat_task.cancel()


async def websocket_heartbeat(websocket: WebSocket, user_id: str):
    """
    WebSocket 心跳检测

    Args:
        websocket: WebSocket 连接
        user_id: 用户 ID
    """
    try:
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
            await websocket.send_json({"type": "ping"})
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"Heartbeat failed for user {user_id}: {e}")


async def handle_client_message(user_id: str, message: dict):
    """
    处理客户端消息

    Args:
        user_id: 用户 ID
        message: 消息内容
    """
    message_type = message.get("type")

    if message_type == "subscribe":
        # 订阅特定主题
        topic = message.get("topic")
        if topic:
            await manager.join_room(user_id, topic)
            logger.info(f"User {user_id} subscribed to {topic}")

    elif message_type == "unsubscribe":
        # 取消订阅
        topic = message.get("topic")
        if topic:
            await manager.leave_room(user_id, topic)
            logger.info(f"User {user_id} unsubscribed from {topic}")

    elif message_type == "ping":
        # 心跳响应
        await manager.send_message(user_id, {"type": "pong"})

    else:
        logger.warning(f"Unknown message type: {message_type}")


# ===== 辅助函数 =====

async def broadcast_to_room(room_id: str, data: dict):
    """
    向房间内所有用户广播消息

    Args:
        room_id: 房间 ID
        data: 消息数据
    """
    await manager.send_to_room(room_id, data)


async def send_to_user(user_id: str, data: dict):
    """
    向指定用户发送消息

    Args:
        user_id: 用户 ID
        data: 消息数据
    """
    await manager.send_message(user_id, data)


# 导出辅助函数供其他模块使用
__all__ = [
    "websocket_endpoint",
    "broadcast_to_room",
    "send_to_user"
]
