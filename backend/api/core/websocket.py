# -*- coding: utf-8 -*-
"""
SupaWriter WebSocket 连接管理器
管理 WebSocket 连接、消息广播、进度推送
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional, Any
import logging
import asyncio
import json

from backend.api.config import settings


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket 连接管理器

    管理所有活跃的 WebSocket 连接，支持：
    - 用户级别连接管理
    - 消息广播
    - 房间管理（可选）
    """

    def __init__(self):
        # 用户 ID -> WebSocket 连接
        self.active_connections: Dict[str, WebSocket] = {}

        # 房间管理（用于广播）
        # room_id -> Set[user_id]
        self.rooms: Dict[str, Set[str]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """
        接受新的 WebSocket 连接

        Args:
            user_id: 用户 ID
            websocket: WebSocket 连接对象
        """
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected: user_id={user_id}")

        # 发送连接成功消息
        await self.send_message(user_id, {
            "type": "connected",
            "message": "WebSocket connection established"
        })

    async def disconnect(self, user_id: str):
        """
        断开 WebSocket 连接

        Args:
            user_id: 用户 ID
        """
        if user_id in self.active_connections:
            # 从所有房间中移除
            for room_id, users in self.rooms.items():
                if user_id in users:
                    users.remove(user_id)

            # 删除连接
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: user_id={user_id}")

    async def send_message(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        向指定用户发送消息

        Args:
            user_id: 用户 ID
            data: 消息数据（字典）

        Returns:
            是否发送成功
        """
        websocket = self.active_connections.get(user_id)
        if websocket is None:
            logger.warning(f"WebSocket not found for user_id={user_id}")
            return False

        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending message to user_id={user_id}: {e}")
            # 发送失败，移除连接
            await self.disconnect(user_id)
            return False

    async def broadcast(self, data: Dict[str, Any], exclude: Optional[Set[str]] = None):
        """
        向所有连接的客户端广播消息

        Args:
            data: 消息数据
            exclude: 要排除的用户 ID 集合
        """
        exclude = exclude or set()
        disconnected_users = []

        for user_id, websocket in self.active_connections.items():
            if user_id in exclude:
                continue

            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to user_id={user_id}: {e}")
                disconnected_users.append(user_id)

        # 清理断开的连接
        for user_id in disconnected_users:
            await self.disconnect(user_id)

    async def send_progress(
        self,
        user_id: str,
        task_id: str,
        progress: int,
        progress_text: str,
        live_article: Optional[str] = None
    ):
        """
        发送文章生成进度更新

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            progress: 进度百分比 (0-100)
            progress_text: 进度描述文本
            live_article: 实时生成的文章内容（可选）
        """
        await self.send_message(user_id, {
            "type": "article_progress",
            "task_id": task_id,
            "progress": progress,
            "progress_text": progress_text,
            "live_article": live_article
        })

    async def send_chat_chunk(self, user_id: str, session_id: str, text: str, is_end: bool = False):
        """
        发送 AI 助手流式响应

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            text: 文本片段
            is_end: 是否结束
        """
        await self.send_message(user_id, {
            "type": "chat_chunk",
            "session_id": session_id,
            "text": text,
            "is_end": is_end
        })

    async def send_queue_update(self, user_id: str, queue_data: Dict[str, Any]):
        """
        发送队列状态更新

        Args:
            user_id: 用户 ID
            queue_data: 队列数据
        """
        await self.send_message(user_id, {
            "type": "queue_update",
            "data": queue_data
        })

    # 房间管理功能

    async def join_room(self, user_id: str, room_id: str):
        """
        用户加入房间

        Args:
            user_id: 用户 ID
            room_id: 房间 ID
        """
        if room_id not in self.rooms:
            self.rooms[room_id] = set()

        self.rooms[room_id].add(user_id)
        logger.info(f"user_id={user_id} joined room={room_id}")

    async def leave_room(self, user_id: str, room_id: str):
        """
        用户离开房间

        Args:
            user_id: 用户 ID
            room_id: 房间 ID
        """
        if room_id in self.rooms and user_id in self.rooms[room_id]:
            self.rooms[room_id].remove(user_id)

            # 如果房间为空，删除房间
            if not self.rooms[room_id]:
                del self.rooms[room_id]

            logger.info(f"user_id={user_id} left room={room_id}")

    async def send_to_room(self, room_id: str, data: Dict[str, Any], exclude: Optional[Set[str]] = None):
        """
        向房间内所有用户发送消息

        Args:
            room_id: 房间 ID
            data: 消息数据
            exclude: 要排除的用户 ID 集合
        """
        exclude = exclude or set()

        if room_id not in self.rooms:
            return

        for user_id in self.rooms[room_id]:
            if user_id not in exclude:
                await self.send_message(user_id, data)

    def get_connected_users(self) -> Set[str]:
        """
        获取所有在线用户 ID

        Returns:
            在线用户 ID 集合
        """
        return set(self.active_connections.keys())

    def is_connected(self, user_id: str) -> bool:
        """
        检查用户是否在线

        Args:
            user_id: 用户 ID

        Returns:
            是否在线
        """
        return user_id in self.active_connections

    def get_connection_count(self) -> int:
        """
        获取当前连接数

        Returns:
            连接数
        """
        return len(self.active_connections)


# 全局连接管理器实例
manager = ConnectionManager()


async def websocket_heartbeat(websocket: WebSocket, interval: int = None):
    """
    WebSocket 心跳检测

    Args:
        websocket: WebSocket 连接
        interval: 心跳间隔（秒），默认使用配置值
    """
    interval = interval or settings.WS_HEARTBEAT_INTERVAL

    try:
        while True:
            await asyncio.sleep(interval)
            await websocket.send_json({"type": "ping"})
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.warning("Heartbeat failed, connection may be closed")
