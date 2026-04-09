# -*- coding: utf-8 -*-
"""
Redis Progress Tracking Utilities for Worker
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from backend.api.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track article generation progress in Redis"""

    def __init__(self, task_id: str, ttl: int = 3600):
        """
        Initialize progress tracker

        Args:
            task_id: Unique task identifier
            ttl: Time to live in seconds (default 1 hour)
        """
        self.task_id = task_id
        self.ttl = ttl
        self.key = f"article:progress:{task_id}"

    async def init(
        self,
        user_id: int,
        topic: str
    ):
        """
        Initialize progress in Redis

        Args:
            user_id: User ID who initiated the task
            topic: Article topic
        """
        await redis_client.async_client.hset(
            self.key,
            mapping={
                "task_id": self.task_id,
                "status": "queued",
                "progress": "0",
                "progress_text": "任务已提交，等待处理...",
                "user_id": str(user_id),
                "topic": topic,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        )
        await redis_client.async_client.expire(self.key, self.ttl)

        # Add task to user's task set
        user_tasks_key = f"article:user:{user_id}:tasks"
        await redis_client.async_client.sadd(user_tasks_key, self.task_id)
        await redis_client.async_client.expire(user_tasks_key, self.ttl)

        logger.debug(f"Progress initialized: {self.task_id}")

    async def update(
        self,
        progress: int,
        step: str,
        data: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None
    ):
        """
        Update progress in Redis

        Args:
            progress: Progress percentage (0-100)
            step: Current step description
            data: Optional additional data to include
            status: Optional status update ('running', 'completed', 'failed')
        """
        update_data = {
            "progress": str(progress),
            "step": step,
            "timestamp": datetime.now().isoformat()
        }
        
        if status:
            update_data["status"] = status

        if data:
            update_data["data"] = json.dumps(data)

        await redis_client.async_client.hset(
            self.key,
            mapping=update_data
        )
        await redis_client.async_client.expire(self.key, self.ttl)

        logger.debug(f"Progress updated: {self.task_id} - {progress}% - {step} - status: {status or 'unchanged'}")

    async def get(self) -> Dict[str, Any]:
        """Get current progress from Redis"""
        data = await redis_client.async_client.hgetall(self.key)

        if not data:
            return {}

        # Parse JSON fields
        if 'data' in data:
            try:
                data['data'] = json.loads(data['data'])
            except json.JSONDecodeError:
                pass

        return data

    async def get_progress(self) -> Dict[str, Any]:
        """
        Get current progress in TaskProgress format

        Returns:
            Dict with all TaskProgress fields
        """
        data = await redis_client.async_client.hgetall(self.key)

        if not data:
            return {
                "task_id": self.task_id,
                "status": "queued",
                "progress": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }

        # Build TaskProgress dict
        result = {
            "task_id": data.get("task_id", self.task_id),
            "status": data.get("status", "queued"),
            "progress": int(data.get("progress", 0)),
            "progress_text": data.get("step") or data.get("progress_text"),
            "created_at": datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            "updated_at": datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        }

        # Parse additional fields from data
        if "data" in data:
            try:
                parsed_data = json.loads(data["data"])
                if parsed_data.get("type") == "search":
                    result["outline"] = {"search_results": parsed_data.get("results")}
                elif parsed_data.get("type") == "outline":
                    result["outline"] = parsed_data.get("outline")
                elif parsed_data.get("type") == "writing":
                    result["live_article"] = parsed_data.get("live_article")
                elif parsed_data.get("type") == "completed":
                    result["live_article"] = parsed_data.get("article", {}).get("content")
                    result["outline"] = parsed_data.get("article", {}).get("outline")
                elif parsed_data.get("type") == "error":
                    result["error"] = parsed_data.get("error_message")
            except json.JSONDecodeError:
                pass

        return result

    async def complete(self, article: Dict[str, Any]):
        """Mark task as completed"""
        await self.update(
            progress=100,
            step="文章生成完成！",
            status="completed",
            data={
                "type": "completed",
                "article": article
            }
        )

    async def error(self, error_message: str):
        """Mark task as failed"""
        await self.update(
            progress=0,
            step=f"生成失败: {error_message}",
            status="failed",
            data={
                "type": "error",
                "error_message": error_message
            }
        )