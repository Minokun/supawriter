# -*- coding: utf-8 -*-
"""
FAISS 索引缓存管理器

采用混合方案：
- FAISS 索引存储在文件系统
- Redis 缓存元数据和状态
- 支持多用户隔离
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

from backend.api.core.redis_client import redis_client

logger = logging.getLogger(__name__)

# TTL 配置（秒）
FAISS_INDEX_TTL = {
    "normal": 3600,      # 1小时 - 正常访问
    "completed": 86400,  # 24小时 - 任务完成
    "failed": 600        # 10分钟 - 任务失败
}


class FaissIndexCache:
    """FAISS 索引缓存管理（混合方案：文件系统 + Redis 元数据）"""

    def __init__(self):
        """初始化缓存管理器"""
        # 进程内内存缓存（避免重复加载）
        self._memory_cache: Dict[str, Any] = {}
        self._base_dir = 'data/faiss'

    async def get_or_load_index(
        self,
        user_id: int,
        task_id: str
    ) -> Optional[Any]:
        """
        获取或加载 FAISS 索引

        流程：
        1. 检查进程内内存缓存
        2. 检查 Redis 元数据
        3. 如已加载且未过期，直接返回
        4. 如未加载，从文件系统加载
        5. 更新 Redis 状态为 "ready"

        Args:
            user_id: 用户 ID
            task_id: 任务 ID

        Returns:
            FAISSIndex 实例或 None
        """
        cache_key = f"{user_id}:{task_id}"

        # 1. 检查进程内内存缓存
        if cache_key in self._memory_cache:
            logger.debug(f"FAISS index from memory cache: {cache_key}")
            return self._memory_cache[cache_key]

        # 2. 检查 Redis 元数据
        meta_key = f"faiss:meta:{user_id}:{task_id}"
        meta = await redis_client.async_client.hgetall(meta_key)

        if meta and meta.get('status') == 'ready':
            # 检查索引文件是否存在
            index_path = meta.get('index_path')
            if index_path and os.path.exists(index_path):
                # 从文件系统加载
                faiss_index = await self._load_from_filesystem(
                    user_id=user_id,
                    task_id=task_id,
                    index_path=index_path
                )
                if faiss_index:
                    # 更新内存缓存
                    self._memory_cache[cache_key] = faiss_index
                    # 刷新 Redis TTL
                    await self._refresh_metadata(user_id, task_id, status="ready")
                    return faiss_index

        logger.warning(f"FAISS index not found for user={user_id}, task={task_id}")
        return None

    async def save_index(
        self,
        user_id: int,
        task_id: str,
        faiss_index: Any,
        status: str = "normal"
    ) -> bool:
        """
        保存 FAISS 索引到文件系统并更新 Redis 元数据

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            faiss_index: FAISSIndex 实例
            status: 任务状态 (normal/completed/failed)

        Returns:
            是否成功保存
        """
        try:
            from utils.embedding_utils import save_faiss_index

            # 保存到文件系统
            success = save_faiss_index(
                faiss_index=faiss_index,
                index_dir=self._base_dir,
                username=str(user_id),
                article_id=task_id
            )

            if not success:
                logger.error(f"Failed to save FAISS index to disk: user={user_id}, task={task_id}")
                return False

            # 构建索引路径
            index_path = os.path.join(self._base_dir, str(user_id), task_id, 'index.faiss')

            # 更新 Redis 元数据
            await self._update_metadata(
                user_id=user_id,
                task_id=task_id,
                status=status,
                index_path=index_path,
                image_count=faiss_index.get_size()
            )

            # 更新内存缓存
            cache_key = f"{user_id}:{task_id}"
            self._memory_cache[cache_key] = faiss_index

            # 添加到用户任务集合
            await redis_client.async_client.sadd(f"faiss:tasks:{user_id}", task_id)

            logger.info(f"FAISS index saved: user={user_id}, task={task_id}, count={faiss_index.get_size()}")
            return True

        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
            return False

    async def mark_task_status(
        self,
        user_id: int,
        task_id: str,
        status: str
    ) -> None:
        """
        标记任务状态并更新 TTL

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            status: 任务状态 (normal/completed/failed)
        """
        await self._refresh_metadata(user_id, task_id, status=status)

    async def delete_index(
        self,
        user_id: int,
        task_id: str
    ) -> bool:
        """
        删除 FAISS 索引（文件系统 + Redis + 内存）

        Args:
            user_id: 用户 ID
            task_id: 任务 ID

        Returns:
            是否成功删除
        """
        try:
            import shutil

            # 1. 删除内存缓存
            cache_key = f"{user_id}:{task_id}"
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]

            # 2. 删除文件系统索引
            index_dir = os.path.join(self._base_dir, str(user_id), task_id)
            if os.path.exists(index_dir):
                shutil.rmtree(index_dir)
                logger.info(f"Deleted FAISS index directory: {index_dir}")

            # 3. 删除 Redis 元数据
            meta_key = f"faiss:meta:{user_id}:{task_id}"
            await redis_client.async_client.delete(meta_key)

            # 4. 从用户任务集合中移除
            await redis_client.async_client.srem(f"faiss:tasks:{user_id}", task_id)

            logger.info(f"FAISS index deleted: user={user_id}, task={task_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting FAISS index: {e}")
            return False

    async def get_user_tasks(self, user_id: int) -> list:
        """
        获取用户的所有 FAISS 任务

        Args:
            user_id: 用户 ID

        Returns:
            任务 ID 列表
        """
        tasks = await redis_client.async_client.smembers(f"faiss:tasks:{user_id}")
        return list(tasks) if tasks else []

    async def _load_from_filesystem(
        self,
        user_id: int,
        task_id: str,
        index_path: str
    ) -> Optional[Any]:
        """从文件系统加载 FAISS 索引"""
        try:
            from utils.embedding_utils import create_faiss_index

            # 使用 create_faiss_index 加载现有索引
            faiss_index = create_faiss_index(
                load_from_disk=True,
                index_dir=self._base_dir,
                username=str(user_id),
                article_id=task_id
            )

            if faiss_index.get_size() > 0:
                logger.info(f"Loaded FAISS index from filesystem: user={user_id}, task={task_id}, size={faiss_index.get_size()}")
                return faiss_index
            else:
                logger.warning(f"FAISS index is empty: user={user_id}, task={task_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to load FAISS index from filesystem: {e}")
            return None

    async def _update_metadata(
        self,
        user_id: int,
        task_id: str,
        status: str,
        index_path: str,
        image_count: int
    ) -> None:
        """更新 Redis 元数据"""
        meta_key = f"faiss:meta:{user_id}:{task_id}"

        ttl = FAISS_INDEX_TTL.get(status, FAISS_INDEX_TTL["normal"])

        metadata = {
            "task_id": task_id,
            "user_id": str(user_id),
            "status": status,
            "image_count": str(image_count),
            "index_path": index_path,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        }

        await redis_client.async_client.hset(meta_key, mapping=metadata)
        await redis_client.async_client.expire(meta_key, ttl)

        logger.debug(f"Updated FAISS metadata: user={user_id}, task={task_id}, status={status}, ttl={ttl}")

    async def _refresh_metadata(
        self,
        user_id: int,
        task_id: str,
        status: str = None
    ) -> None:
        """刷新 Redis 元数据（更新 TTL 和最后访问时间）"""
        meta_key = f"faiss:meta:{user_id}:{task_id}"
        meta = await redis_client.async_client.hgetall(meta_key)

        if not meta:
            logger.warning(f"No metadata found for refresh: user={user_id}, task={task_id}")
            return

        # 确定新的状态和 TTL
        new_status = status or meta.get('status', 'normal')
        ttl = FAISS_INDEX_TTL.get(new_status, FAISS_INDEX_TTL["normal"])

        # 更新最后访问时间
        update_data = {
            "last_accessed": datetime.now().isoformat()
        }
        if status:
            update_data["status"] = status

        await redis_client.async_client.hset(meta_key, mapping=update_data)
        await redis_client.async_client.expire(meta_key, ttl)

        logger.debug(f"Refreshed FAISS metadata: user={user_id}, task={task_id}, status={new_status}")

    def clear_memory_cache(self, user_id: int = None, task_id: str = None) -> None:
        """
        清除内存缓存

        Args:
            user_id: 可选，指定用户 ID
            task_id: 可选，指定任务 ID
        """
        if user_id and task_id:
            cache_key = f"{user_id}:{task_id}"
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
                logger.debug(f"Cleared memory cache: {cache_key}")
        else:
            self._memory_cache.clear()
            logger.debug("Cleared all memory cache")


# 全局实例
faiss_cache = FaissIndexCache()


async def cleanup_expired_faiss_indexes(ctx=None) -> dict:
    """
    定期清理过期的 FAISS 索引（Cron 任务）

    清理逻辑：
    1. 扫描所有 faiss:meta:* 键
    2. 检查 TTL 是否过期
    3. 删除过期的索引文件和 Redis 元数据

    Args:
        ctx: Arq context (passed by cron job, not used but required)

    Returns:
        清理统计信息
    """
    import shutil
    from pathlib import Path

    stats = {
        "scanned": 0,
        "cleaned": 0,
        "errors": 0
    }

    try:
        # 扫描所有 faiss:meta:* 键
        pattern = "faiss:meta:*"
        async for key in redis_client.async_client.scan_iter(match=pattern, count=100):
            stats["scanned"] += 1

            # 解析 key 获取 user_id 和 task_id
            # 格式: faiss:meta:{user_id}:{task_id}
            parts = key.split(":")
            if len(parts) < 4:
                continue

            user_id = parts[2]
            task_id = parts[3]

            # 检查是否过期（TTL 为 0 表示已过期）
            ttl = await redis_client.async_client.ttl(key)

            if ttl == -2 or ttl == -1:
                # 键不存在或没有设置过期时间，跳过
                continue
            elif ttl > 0:
                # 未过期，跳过
                continue

            # TTL 已过期，清理索引
            logger.info(f"Cleaning up expired FAISS index: user={user_id}, task={task_id}")

            try:
                # 1. 删除文件系统索引
                index_dir = os.path.join('data/faiss', user_id, task_id)
                if os.path.exists(index_dir):
                    shutil.rmtree(index_dir)
                    logger.debug(f"Deleted index directory: {index_dir}")

                # 2. 删除 Redis 元数据
                await redis_client.async_client.delete(key)

                # 3. 从用户任务集合中移除
                await redis_client.async_client.srem(f"faiss:tasks:{user_id}", task_id)

                # 4. 清除内存缓存
                cache_key = f"{user_id}:{task_id}"
                if cache_key in faiss_cache._memory_cache:
                    del faiss_cache._memory_cache[cache_key]

                stats["cleaned"] += 1
                logger.info(f"Successfully cleaned FAISS index: user={user_id}, task={task_id}")

            except Exception as e:
                logger.error(f"Error cleaning FAISS index user={user_id}, task={task_id}: {e}")
                stats["errors"] += 1

        logger.info(f"FAISS cleanup completed: scanned={stats['scanned']}, cleaned={stats['cleaned']}, errors={stats['errors']}")
        return stats

    except Exception as e:
        logger.error(f"FAISS cleanup failed: {e}")
        stats["errors"] += 1
        return stats
