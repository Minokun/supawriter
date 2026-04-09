# -*- coding: utf-8 -*-
"""
Redis 图片URL临时存储
用于在搜索和索引创建之间传递图片数据
"""

import logging
from typing import List, Dict, Optional
from backend.api.core.redis_client import redis_client

logger = logging.getLogger(__name__)

# Redis Key 前缀
IMAGE_LIST_KEY = "faiss:images"
IMAGE_META_KEY = "faiss:images:meta"

# TTL 配置
IMAGE_TTL = 3600  # 1小时


class RedisImageStore:
    """Redis 图片URL临时存储"""

    def _get_list_key(self, user_id: int, task_id: str) -> str:
        """获取图片列表的Redis key"""
        return f"{IMAGE_LIST_KEY}:{user_id}:{task_id}"

    def _get_meta_key(self, user_id: int, task_id: str) -> str:
        """获取元数据的Redis key"""
        return f"{IMAGE_META_KEY}:{user_id}:{task_id}"

    async def add_images(
        self,
        user_id: int,
        task_id: str,
        image_urls: List[str]
    ) -> int:
        """
        添加图片URL到Redis（自动去重）

        Args:
            user_id: 用户ID
            task_id: 任务ID
            image_urls: 图片URL列表

        Returns:
            实际添加的数量（去重后）
        """
        if not image_urls:
            return 0

        list_key = self._get_list_key(user_id, task_id)

        try:
            # 批量添加（Redis会自动去重）
            count = 0
            for url in image_urls:
                if url and url.strip():
                    added = await redis_client.async_client.sadd(list_key, url.strip())
                    count += added

            # 设置过期时间
            await redis_client.async_client.expire(list_key, IMAGE_TTL)

            # 更新元数据
            await self._update_metadata(user_id, task_id, {
                "total_count": str(await self.get_count(user_id, task_id)),
                "status": "collecting"
            })

            logger.debug(f"Added {count} images to Redis for user={user_id}, task={task_id}")
            return count

        except Exception as e:
            logger.error(f"Error adding images to Redis: {e}")
            return 0

    async def get_images(
        self,
        user_id: int,
        task_id: str
    ) -> List[str]:
        """
        获取所有图片URL

        Args:
            user_id: 用户ID
            task_id: 任务ID

        Returns:
            图片URL列表
        """
        list_key = self._get_list_key(user_id, task_id)

        try:
            members = await redis_client.async_client.smembers(list_key)
            return list(members) if members else []

        except Exception as e:
            logger.error(f"Error getting images from Redis: {e}")
            return []

    async def get_count(
        self,
        user_id: int,
        task_id: str
    ) -> int:
        """获取图片数量"""
        list_key = self._get_list_key(user_id, task_id)

        try:
            return await redis_client.async_client.scard(list_key)
        except Exception as e:
            logger.error(f"Error getting image count: {e}")
            return 0

    async def mark_ready(
        self,
        user_id: int,
        task_id: str,
        image_count: int
    ) -> None:
        """
        标记索引创建完成

        Args:
            user_id: 用户ID
            task_id: 任务ID
            image_count: 成功索引的图片数量
        """
        await self._update_metadata(user_id, task_id, {
            "indexed_count": str(image_count),
            "status": "ready"
        })

        logger.info(f"Marked index ready for user={user_id}, task={task_id}, count={image_count}")

    async def get_status(
        self,
        user_id: int,
        task_id: str
    ) -> Dict:
        """
        获取索引状态

        Returns:
            状态字典: {total_count, indexed_count, status}
        """
        meta_key = self._get_meta_key(user_id, task_id)

        try:
            meta = await redis_client.async_client.hgetall(meta_key)
            return {
                "total_count": int(meta.get("total_count", 0)),
                "indexed_count": int(meta.get("indexed_count", 0)),
                "status": meta.get("status", "unknown")
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"status": "error"}

    async def delete_images(
        self,
        user_id: int,
        task_id: str
    ) -> bool:
        """
        Delete all images for a user/task

        Args:
            user_id: 用户ID
            task_id: 任务ID

        Returns:
            是否成功删除
        """
        try:
            list_key = self._get_list_key(user_id, task_id)
            meta_key = self._get_meta_key(user_id, task_id)

            # Delete image list and metadata
            await redis_client.async_client.delete(list_key)
            await redis_client.async_client.delete(meta_key)

            logger.debug(f"Deleted images from Redis: user={user_id}, task={task_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting images from Redis: {e}")
            return False

    async def _update_metadata(
        self,
        user_id: int,
        task_id: str,
        data: Dict[str, str]
    ) -> None:
        """更新元数据"""
        meta_key = self._get_meta_key(user_id, task_id)

        try:
            await redis_client.async_client.hset(meta_key, mapping=data)
            await redis_client.async_client.expire(meta_key, IMAGE_TTL)
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")


# 全局实例
redis_image_store = RedisImageStore()
