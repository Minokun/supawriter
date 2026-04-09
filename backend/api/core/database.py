# -*- coding: utf-8 -*-
"""
SupaWriter FastAPI 数据库连接管理
复用现有的 utils.database 模块
"""

from typing import Optional
from contextlib import contextmanager
import logging

# 导入现有的数据库模块
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.database import Database


logger = logging.getLogger(__name__)


def get_db_url() -> Optional[str]:
    """
    获取数据库 URL

    Returns:
        数据库 URL 字符串
    """
    import os

    # 优先从环境变量获取
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url

    # 从单独的配置项构建 URL
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    database = os.getenv('POSTGRES_DB', 'supawriter')
    user = os.getenv('POSTGRES_USER', 'supawriter')
    password = os.getenv('POSTGRES_PASSWORD', '')

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


@contextmanager
def get_db_connection():
    """
    获取数据库连接的上下文管理器

    用于 FastAPI 路由中

    Yields:
        数据库连接对象
    """
    with Database.get_connection() as conn:
        yield conn


@contextmanager
def get_db_cursor(cursor_factory=None):
    """
    获取数据库游标的上下文管理器

    用于 FastAPI 路由中

    Args:
        cursor_factory: 游标工厂（可选）

    Yields:
        数据库游标对象
    """
    from psycopg2.extras import RealDictCursor

    if cursor_factory is None:
        cursor_factory = RealDictCursor

    with Database.get_cursor(cursor_factory=cursor_factory) as cursor:
        yield cursor


async def init_db_pool():
    """
    初始化数据库连接池

    在 FastAPI 启动时调用
    """
    try:
        Database.get_connection_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


async def close_db_pool():
    """
    关闭数据库连接池

    在 FastAPI 关闭时调用
    """
    try:
        if Database._connection_pool is not None:
            Database._connection_pool.closeall()
            Database._connection_pool = None
            logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Error closing database pool: {e}")


# 数据库依赖项（用于 FastAPI Depends）
def get_db():
    """
    FastAPI 依赖项：获取数据库连接

    用法:
        @router.get("/users")
        def get_users(db = Depends(get_db)):
            with get_db_cursor() as cursor:
                cursor.execute("SELECT * FROM users")
                return cursor.fetchall()

    Returns:
        数据库连接上下文管理器
    """
    return get_db_connection


def get_db_ctx():
    """
    FastAPI 依赖项：获取数据库游标

    用法:
        @router.get("/users")
        def get_users(db_cursor = Depends(get_db_ctx)):
            with db_cursor as cursor:
                cursor.execute("SELECT * FROM users")
                return cursor.fetchall()

    Returns:
        数据库游标上下文管理器
    """
    return get_db_cursor
