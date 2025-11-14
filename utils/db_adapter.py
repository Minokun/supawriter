"""
数据库适配器 - 支持 PostgreSQL 和文件存储的混合模式
适用于从 JSON 文件平滑迁移到 PostgreSQL
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

try:
    import asyncpg
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logging.warning("PostgreSQL 依赖未安装，将使用文件存储模式")

from .history_utils import (
    load_user_history, save_user_history, add_history_record,
    delete_history_record, load_chat_session, save_chat_session,
    create_chat_session, list_chat_sessions, delete_chat_session
)

class DatabaseAdapter:
    """数据库适配器 - 支持 PostgreSQL 和文件存储"""
    
    def __init__(self):
        self.use_postgres = self._should_use_postgres()
        self.connection_pool = None
        self.logger = logging.getLogger(__name__)
        
        if self.use_postgres:
            self._init_postgres()
        else:
            self.logger.info("使用文件存储模式")
    
    def _should_use_postgres(self) -> bool:
        """判断是否应该使用 PostgreSQL"""
        if not POSTGRES_AVAILABLE:
            return False
        
        # 检查环境变量
        database_url = os.getenv('DATABASE_URL')
        postgres_host = os.getenv('POSTGRES_HOST')
        
        return bool(database_url or postgres_host)
    
    def _init_postgres(self):
        """初始化 PostgreSQL 连接"""
        try:
            # 获取数据库连接信息
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                self.db_config = database_url
            else:
                self.db_config = {
                    'host': os.getenv('POSTGRES_HOST', 'localhost'),
                    'port': int(os.getenv('POSTGRES_PORT', 5432)),
                    'database': os.getenv('POSTGRES_DB', 'supawriter'),
                    'user': os.getenv('POSTGRES_USER', 'supawriter'),
                    'password': os.getenv('POSTGRES_PASSWORD', '')
                }
            
            # 测试连接
            self._test_connection()
            self.logger.info("PostgreSQL 连接配置成功")
            
        except Exception as e:
            self.logger.error(f"PostgreSQL 初始化失败: {e}")
            self.use_postgres = False
    
    def _test_connection(self):
        """测试数据库连接"""
        if isinstance(self.db_config, str):
            conn = psycopg2.connect(self.db_config)
        else:
            conn = psycopg2.connect(**self.db_config)
        
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            if result[0] != 1:
                raise Exception("数据库连接测试失败")
        
        conn.close()
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接（异步）"""
        if not self.use_postgres:
            yield None
            return
        
        if isinstance(self.db_config, str):
            conn = await asyncpg.connect(self.db_config)
        else:
            conn = await asyncpg.connect(**self.db_config)
        
        try:
            yield conn
        finally:
            await conn.close()
    
    def get_sync_connection(self):
        """获取同步数据库连接"""
        if not self.use_postgres:
            return None
        
        if isinstance(self.db_config, str):
            return psycopg2.connect(self.db_config)
        else:
            return psycopg2.connect(**self.db_config)
    
    # ==================== 文章管理 ====================
    
    async def add_article(self, username: str, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加文章"""
        if self.use_postgres:
            return await self._add_article_postgres(username, article_data)
        else:
            return self._add_article_file(username, article_data)
    
    async def _add_article_postgres(self, username: str, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """PostgreSQL 添加文章"""
        async with self.get_connection() as conn:
            query = """
                INSERT INTO articles (
                    username, topic, article_content, summary, tags, metadata,
                    model_type, model_name, write_type, spider_num, custom_style,
                    is_transformed, original_article_id, image_task_id, image_enabled,
                    image_similarity_threshold, image_max_count, article_topic
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                ) RETURNING *
            """
            
            result = await conn.fetchrow(
                query,
                username,
                article_data.get('topic', ''),
                article_data.get('article_content', ''),
                article_data.get('summary'),
                article_data.get('tags', []),
                json.dumps(article_data.get('metadata', {})),
                article_data.get('model_type'),
                article_data.get('model_name'),
                article_data.get('write_type'),
                article_data.get('spider_num'),
                article_data.get('custom_style'),
                article_data.get('is_transformed', False),
                article_data.get('original_article_id'),
                article_data.get('image_task_id'),
                article_data.get('image_enabled', False),
                article_data.get('image_similarity_threshold'),
                article_data.get('image_max_count'),
                article_data.get('article_topic')
            )
            
            return dict(result)
    
    def _add_article_file(self, username: str, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """文件存储添加文章"""
        return add_history_record(
            username=username,
            topic=article_data.get('topic', ''),
            article_content=article_data.get('article_content', ''),
            summary=article_data.get('summary'),
            model_type=article_data.get('model_type'),
            model_name=article_data.get('model_name'),
            write_type=article_data.get('write_type'),
            spider_num=article_data.get('spider_num'),
            custom_style=article_data.get('custom_style'),
            is_transformed=article_data.get('is_transformed', False),
            original_article_id=article_data.get('original_article_id'),
            image_task_id=article_data.get('image_task_id'),
            image_enabled=article_data.get('image_enabled', False),
            image_similarity_threshold=article_data.get('image_similarity_threshold'),
            image_max_count=article_data.get('image_max_count'),
            tags=article_data.get('tags'),
            article_topic=article_data.get('article_topic')
        )
    
    async def get_user_articles(self, username: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取用户文章列表"""
        if self.use_postgres:
            return await self._get_user_articles_postgres(username, limit, offset)
        else:
            return self._get_user_articles_file(username, limit, offset)
    
    async def _get_user_articles_postgres(self, username: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """PostgreSQL 获取用户文章"""
        async with self.get_connection() as conn:
            query = """
                SELECT id, username, topic, 
                       LEFT(article_content, 200) as preview,
                       summary, tags, created_at, updated_at,
                       model_type, model_name, write_type
                FROM articles 
                WHERE username = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            
            rows = await conn.fetch(query, username, limit, offset)
            return [dict(row) for row in rows]
    
    def _get_user_articles_file(self, username: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """文件存储获取用户文章"""
        history = load_user_history(username)
        # 按时间倒序排序
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 分页
        start = offset
        end = offset + limit
        page_history = history[start:end]
        
        # 转换格式并截取预览
        result = []
        for item in page_history:
            content = item.get('article_content', '')
            preview = content[:200] + '...' if len(content) > 200 else content
            
            result.append({
                'id': item.get('id'),
                'username': username,
                'topic': item.get('topic', ''),
                'preview': preview,
                'summary': item.get('summary'),
                'tags': item.get('tags', []),
                'created_at': item.get('timestamp'),
                'updated_at': item.get('timestamp'),
                'model_type': item.get('model_type'),
                'model_name': item.get('model_name'),
                'write_type': item.get('write_type')
            })
        
        return result
    
    async def search_articles(self, username: str, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索文章"""
        if self.use_postgres:
            return await self._search_articles_postgres(username, keyword, limit)
        else:
            return self._search_articles_file(username, keyword, limit)
    
    async def _search_articles_postgres(self, username: str, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """PostgreSQL 全文搜索"""
        async with self.get_connection() as conn:
            # 使用自定义的全文搜索函数
            rows = await conn.fetch(
                "SELECT * FROM search_articles_fulltext($1, $2, $3)",
                keyword, username, limit
            )
            return [dict(row) for row in rows]
    
    def _search_articles_file(self, username: str, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """文件存储搜索"""
        history = load_user_history(username)
        results = []
        
        keyword_lower = keyword.lower()
        
        for item in history:
            # 简单的关键词匹配
            title = item.get('topic', '').lower()
            content = item.get('article_content', '').lower()
            summary = item.get('summary', '').lower()
            
            if (keyword_lower in title or 
                keyword_lower in content or 
                keyword_lower in summary):
                
                results.append({
                    'id': item.get('id'),
                    'username': username,
                    'topic': item.get('topic', ''),
                    'article_content': item.get('article_content', ''),
                    'summary': item.get('summary'),
                    'tags': item.get('tags', []),
                    'created_at': item.get('timestamp'),
                    'rank': 1.0  # 简单排序
                })
        
        # 按相关性排序（这里简化为按时间）
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return results[:limit]
    
    async def delete_article(self, username: str, article_id: str) -> bool:
        """删除文章"""
        if self.use_postgres:
            return await self._delete_article_postgres(username, article_id)
        else:
            return self._delete_article_file(username, article_id)
    
    async def _delete_article_postgres(self, username: str, article_id: str) -> bool:
        """PostgreSQL 删除文章"""
        async with self.get_connection() as conn:
            result = await conn.execute(
                "DELETE FROM articles WHERE id = $1 AND username = $2",
                article_id, username
            )
            return result == "DELETE 1"
    
    def _delete_article_file(self, username: str, article_id: str) -> bool:
        """文件存储删除文章"""
        try:
            article_id_int = int(article_id)
            return delete_history_record(username, article_id_int)
        except ValueError:
            return False
    
    # ==================== 聊天管理 ====================
    
    async def create_chat(self, username: str, title: str = None) -> Dict[str, Any]:
        """创建聊天会话"""
        if self.use_postgres:
            return await self._create_chat_postgres(username, title)
        else:
            return create_chat_session(username, title)
    
    async def _create_chat_postgres(self, username: str, title: str) -> Dict[str, Any]:
        """PostgreSQL 创建聊天"""
        async with self.get_connection() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO chat_sessions (username, title, messages)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                username, title or 'New Chat', json.dumps([])
            )
            return dict(result)
    
    async def get_user_chats(self, username: str) -> List[Dict[str, Any]]:
        """获取用户聊天列表"""
        if self.use_postgres:
            return await self._get_user_chats_postgres(username)
        else:
            return list_chat_sessions(username)
    
    async def _get_user_chats_postgres(self, username: str) -> List[Dict[str, Any]]:
        """PostgreSQL 获取聊天列表"""
        async with self.get_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, created_at, updated_at,
                       jsonb_array_length(messages) as message_count
                FROM chat_sessions 
                WHERE username = $1
                ORDER BY updated_at DESC
                """,
                username
            )
            return [dict(row) for row in rows]
    
    # ==================== 统计信息 ====================
    
    async def get_user_stats(self, username: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        if self.use_postgres:
            return await self._get_user_stats_postgres(username)
        else:
            return self._get_user_stats_file(username)
    
    async def _get_user_stats_postgres(self, username: str) -> Dict[str, Any]:
        """PostgreSQL 获取统计"""
        async with self.get_connection() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM article_stats WHERE username = $1",
                username
            )
            return dict(result) if result else {}
    
    def _get_user_stats_file(self, username: str) -> Dict[str, Any]:
        """文件存储获取统计"""
        history = load_user_history(username)
        
        if not history:
            return {
                'total_articles': 0,
                'articles_last_7_days': 0,
                'articles_last_30_days': 0,
                'avg_content_length': 0,
                'last_article_date': None
            }
        
        from datetime import datetime, timedelta
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        total = len(history)
        last_7_days = 0
        last_30_days = 0
        total_length = 0
        last_date = None
        
        for item in history:
            timestamp_str = item.get('timestamp', '')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if timestamp > week_ago:
                        last_7_days += 1
                    if timestamp > month_ago:
                        last_30_days += 1
                    
                    if not last_date or timestamp > last_date:
                        last_date = timestamp
                except:
                    pass
            
            content = item.get('article_content', '')
            total_length += len(content)
        
        return {
            'total_articles': total,
            'articles_last_7_days': last_7_days,
            'articles_last_30_days': last_30_days,
            'avg_content_length': total_length / total if total > 0 else 0,
            'last_article_date': last_date.isoformat() if last_date else None
        }

# 全局实例
db_adapter = DatabaseAdapter()

# 便捷函数
async def add_article(username: str, article_data: Dict[str, Any]) -> Dict[str, Any]:
    """添加文章"""
    return await db_adapter.add_article(username, article_data)

async def get_user_articles(username: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """获取用户文章"""
    return await db_adapter.get_user_articles(username, limit, offset)

async def search_articles(username: str, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """搜索文章"""
    return await db_adapter.search_articles(username, keyword, limit)

async def delete_article(username: str, article_id: str) -> bool:
    """删除文章"""
    return await db_adapter.delete_article(username, article_id)
