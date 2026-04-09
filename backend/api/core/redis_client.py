# -*- coding: utf-8 -*-
"""Redis 异步客户端"""

import redis.asyncio as aioredis
import redis
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

from backend.api.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端（支持同步和异步）"""

    def __init__(self):
        """初始化 Redis 连接"""
        self._async_client = None
        self._sync_client = None

    @property
    def sync_client(self) -> redis.Redis:
        """获取同步客户端"""
        if self._sync_client is None:
            self._sync_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
        return self._sync_client

    @property
    def async_client(self) -> aioredis.Redis:
        """获取异步客户端"""
        if self._async_client is None:
            self._async_client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
        return self._async_client

    def ping(self) -> bool:
        """测试连接（同步）"""
        try:
            return self.sync_client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def async_ping(self) -> bool:
        """测试连接（异步）"""
        try:
            return await self.async_client.ping()
        except Exception as e:
            logger.error(f"Redis async ping failed: {e}")
            return False

    # ============ 文章进度相关 ============

    async def set_article_progress(self, article_id: str, data: Dict[str, Any], ttl: int = 1800):
        """设置文章生成进度（默认30分钟）"""
        key = f"article:progress:{article_id}"
        now_iso = datetime.utcnow().isoformat()
        
        # 根据状态调整 TTL
        if data.get("status") == "completed":
            ttl = 86400  # 完成后保留 24 小时
        elif data.get("status") == "failed":
            ttl = 3600   # 失败后保留 1 小时

        # 自动补充时间戳，便于识别僵尸任务
        if "created_at" not in data:
            existing_created_at = await self.async_client.hget(key, "created_at")
            if existing_created_at:
                data["created_at"] = existing_created_at
            else:
                data["created_at"] = now_iso
        data["updated_at"] = now_iso

        # 转换所有值为字符串
        str_data = {k: str(v) if v is not None else "" for k, v in data.items()}
        
        await self.async_client.hset(key, mapping=str_data)
        await self.async_client.expire(key, ttl)

    async def get_article_progress(self, article_id: str) -> Optional[Dict[str, Any]]:
        """获取文章生成进度"""
        key = f"article:progress:{article_id}"
        data = await self.async_client.hgetall(key)
        return data if data else None

    async def delete_article_progress(self, article_id: str):
        """删除文章进度"""
        key = f"article:progress:{article_id}"
        await self.async_client.delete(key)

    async def get_all_article_progress(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取所有文章进度（可选过滤用户）

        Args:
            user_id: 用户 ID，如果提供则只返回该用户的任务

        Returns:
            任务列表
        """
        tasks = []
        pattern = "article:progress:*"

        # 使用 SCAN 遍历所有进度键
        async for key in self.async_client.scan_iter(match=pattern, count=100):
            data = await self.async_client.hgetall(key)
            if data:
                # 提取 task_id
                task_id = data.get('task_id', key.split(':')[-1])

                # 过滤用户
                if user_id is not None:
                    task_user_id = data.get('user_id')
                    if task_user_id != str(user_id):
                        continue

                # 解析进度数据
                task = {
                    'task_id': task_id,
                    'topic': data.get('topic', ''),
                    'progress': int(data.get('progress', 0)) if data.get('progress', '').isdigit() else 0,
                    'step': data.get('step', ''),
                    'status': data.get('status', 'queued'),
                    'user_id': int(data.get('user_id', 0)) if data.get('user_id', '').isdigit() else 0,
                    'timestamp': data.get('timestamp', ''),
                    'error': data.get('error', '') if data.get('status') == 'failed' else None
                }

                # 尝试解析 data 字段
                data_str = data.get('data', '')
                if data_str:
                    try:
                        task['data'] = json.loads(data_str)
                    except:
                        pass

                tasks.append(task)

        # 按时间戳排序（最新的在前）
        tasks.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return tasks

    # ============ 用户队列相关 ============

    async def add_to_user_queue(self, user_id: int, article_id: str, score: float = None):
        """添加到用户队列"""
        if score is None:
            score = datetime.now().timestamp()
        key = f"user:queue:{user_id}"
        await self.async_client.zadd(key, {article_id: score})
        await self.async_client.expire(key, 604800)  # 7 天过期

    async def get_user_queue(self, user_id: int, limit: int = 20) -> List[tuple]:
        """获取用户队列"""
        key = f"user:queue:{user_id}"
        items = await self.async_client.zrevrange(key, 0, limit - 1, withscores=True)
        return items

    async def remove_from_queue(self, user_id: int, article_id: str):
        """从用户队列中移除"""
        key = f"user:queue:{user_id}"
        await self.async_client.zrem(key, article_id)

    # ============ 热点缓存相关 ============

    async def cache_hotspots(self, source: str, data: List[Dict], ttl: int = 300):
        """缓存热点数据（默认5分钟）"""
        key = f"hotspots:{source}"
        await self.async_client.set(key, json.dumps(data, ensure_ascii=False), ex=ttl)

    async def get_cached_hotspots(self, source: str) -> Optional[List[Dict]]:
        """获取缓存的热点数据"""
        key = f"hotspots:{source}"
        data = await self.async_client.get(key)
        if data:
            return json.loads(data)
        return None

    # ============ 草稿相关 ============

    async def set_draft(self, user_id: int, article_id: str, content: str, ttl: int = 604800):
        """保存草稿（默认7天）"""
        key = f"draft:{user_id}:{article_id}"
        data = {
            "content": content,
            "last_saved": datetime.now().isoformat()
        }
        await self.async_client.set(key, json.dumps(data, ensure_ascii=False), ex=ttl)

    async def get_draft(self, user_id: int, article_id: str) -> Optional[Dict[str, Any]]:
        """获取草稿"""
        key = f"draft:{user_id}:{article_id}"
        data = await self.async_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def close(self):
        """关闭连接"""
        if self._async_client:
            await self._async_client.close()
        if self._sync_client:
            self._sync_client.close()


# 全局实例
redis_client = RedisClient()
