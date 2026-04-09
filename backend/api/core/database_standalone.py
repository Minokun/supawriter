"""
独立的数据库工具模块（不依赖 utils 和 Streamlit）
"""
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Optional, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)


class DatabaseStandalone:
    """独立的数据库管理类"""
    
    _connection = None
    
    @classmethod
    def get_connection(cls):
        """获取数据库连接"""
        if cls._connection is None or cls._connection.closed:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable not set")
            
            cls._connection = psycopg2.connect(database_url)
            logger.info("Database connection established")
        
        return cls._connection
    
    @classmethod
    @contextmanager
    def get_cursor(cls, cursor_factory=None):
        """获取数据库游标的上下文管理器"""
        conn = cls.get_connection()
        cursor = conn.cursor(cursor_factory=cursor_factory or psycopg2.extras.RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    @classmethod
    def close(cls):
        """关闭数据库连接"""
        if cls._connection and not cls._connection.closed:
            cls._connection.close()
            logger.info("Database connection closed")


# 兼容性别名
Database = DatabaseStandalone
get_db_cursor = DatabaseStandalone.get_cursor
