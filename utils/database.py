# -*- coding: utf-8 -*-
"""
数据库连接和模型管理模块
支持PostgreSQL连接和ORM操作
"""

import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path
import streamlit as st

logger = logging.getLogger(__name__)


def load_env_file():
    """从deployment/.env文件加载环境变量"""
    try:
        # 获取项目根目录
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        env_file = project_root / 'deployment' / '.env'
        
        if not env_file.exists():
            logger.debug(f"配置文件不存在: {env_file}")
            return
        
        logger.debug(f"加载配置文件: {env_file}")
        
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析 KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除行内注释（#开头的部分）
                    if '#' in value:
                        # 检查是否在引号内
                        if not ((value.startswith('"') or value.startswith("'"))):
                            value = value.split('#')[0].strip()
                    
                    # 移除引号
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # 只有当环境变量不存在时才设置
                    if key and not os.getenv(key):
                        os.environ[key] = value
                        logger.debug(f"设置环境变量: {key}={value}")
        
        logger.debug("配置文件加载成功")
        
    except Exception as e:
        logger.debug(f"加载配置文件失败: {e}")


# 自动加载环境变量
load_env_file()


class Database:
    """数据库连接池管理器"""
    
    _connection_pool = None
    
    @classmethod
    @st.cache_resource(show_spinner=False)
    def get_connection_pool(cls):
        """获取或创建数据库连接池（使用Streamlit缓存避免重复初始化）"""
        if cls._connection_pool is None:
            try:
                # 优先从环境变量获取数据库URL
                database_url = os.getenv('DATABASE_URL')
                
                if not database_url:
                    # 从secrets获取
                    try:
                        database_url = st.secrets.get('DATABASE_URL')
                    except:
                        pass
                
                if not database_url:
                    # 从单独的配置项构建URL
                    try:
                        db_config = st.secrets.get('postgres', {})
                        if not db_config:
                            # 从环境变量构建
                            db_config = {
                                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                                'port': os.getenv('POSTGRES_PORT', '5432'),
                                'database': os.getenv('POSTGRES_DB', 'supawriter'),
                                'user': os.getenv('POSTGRES_USER', 'supawriter'),
                                'password': os.getenv('POSTGRES_PASSWORD', '')
                            }
                        
                        database_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                    except Exception as e:
                        logger.error(f"无法构建数据库连接URL: {e}")
                        raise
                
                # 创建连接池
                cls._connection_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=database_url
                )
                logger.debug("✅ 数据库连接池创建成功")
            except Exception as e:
                logger.error(f"❌ 创建数据库连接池失败: {e}")
                raise
        
        return cls._connection_pool
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """获取数据库连接（上下文管理器）"""
        pool_obj = cls.get_connection_pool()
        conn = pool_obj.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库事务失败: {e}")
            raise
        finally:
            pool_obj.putconn(conn)
    
    @classmethod
    @contextmanager
    def get_cursor(cls, cursor_factory=RealDictCursor):
        """获取数据库游标（上下文管理器）"""
        with cls.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()


class User:
    """用户模型类"""
    
    @staticmethod
    def create_user(
        username: str,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        motto: Optional[str] = None
    ) -> Optional[int]:
        """
        创建新用户
        
        Args:
            username: 用户名（唯一）
            email: 邮箱
            password_hash: 密码哈希
            display_name: 显示名称
            avatar_url: 头像URL
            motto: 座右铭
        
        Returns:
            创建的用户ID，失败返回None
        """
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, display_name, avatar_url, motto, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (username, email, password_hash, display_name, avatar_url, motto or "创作改变世界"))
                
                result = cursor.fetchone()
                return result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"创建用户失败，用户名或邮箱已存在: {e}")
            return None
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return None
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"查询用户失败: {e}")
            return None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱获取用户信息"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"查询用户失败: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取用户信息"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"查询用户失败: {e}")
            return None
    
    @staticmethod
    def update_user(user_id: int, **kwargs) -> bool:
        """更新用户信息"""
        if not kwargs:
            return False
        
        # 构建更新语句
        set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
        set_clause += ", updated_at = NOW()"
        values = list(kwargs.values()) + [user_id]
        
        try:
            with Database.get_cursor() as cursor:
                cursor.execute(f"""
                    UPDATE users SET {set_clause}
                    WHERE id = %s
                """, values)
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            return False
    
    @staticmethod
    def update_last_login(user_id: int) -> bool:
        """更新最后登录时间"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE users SET last_login = NOW(), updated_at = NOW()
                    WHERE id = %s
                """, (user_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新最后登录时间失败: {e}")
            return False


class OAuthAccount:
    """OAuth账号模型类"""
    
    @staticmethod
    def create_oauth_account(
        user_id: int,
        provider: str,
        provider_user_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> Optional[int]:
        """
        创建OAuth账号绑定
        
        Args:
            user_id: 用户ID
            provider: OAuth提供商（google, wechat等）
            provider_user_id: 提供商的用户ID
            access_token: 访问令牌
            refresh_token: 刷新令牌
            extra_data: 额外数据（JSON格式）
        
        Returns:
            创建的OAuth账号ID，失败返回None
        """
        try:
            import json
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO oauth_accounts 
                    (user_id, provider, provider_user_id, access_token, refresh_token, extra_data, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (user_id, provider, provider_user_id, access_token, refresh_token, 
                      json.dumps(extra_data) if extra_data else None))
                
                result = cursor.fetchone()
                return result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"OAuth账号已绑定: {e}")
            return None
        except Exception as e:
            logger.error(f"创建OAuth账号失败: {e}")
            return None
    
    @staticmethod
    def get_oauth_account(provider: str, provider_user_id: str) -> Optional[Dict[str, Any]]:
        """根据提供商和提供商用户ID获取OAuth账号"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM oauth_accounts 
                    WHERE provider = %s AND provider_user_id = %s
                """, (provider, provider_user_id))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"查询OAuth账号失败: {e}")
            return None
    
    @staticmethod
    def get_user_oauth_accounts(user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有OAuth账号"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM oauth_accounts 
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"查询用户OAuth账号失败: {e}")
            return []
    
    @staticmethod
    def update_oauth_tokens(
        oauth_id: int,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None
    ) -> bool:
        """更新OAuth令牌"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE oauth_accounts 
                    SET access_token = %s, refresh_token = %s, updated_at = NOW()
                    WHERE id = %s
                """, (access_token, refresh_token, oauth_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新OAuth令牌失败: {e}")
            return False
    
    @staticmethod
    def delete_oauth_account(oauth_id: int) -> bool:
        """删除OAuth账号绑定"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("DELETE FROM oauth_accounts WHERE id = %s", (oauth_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除OAuth账号失败: {e}")
            return False
