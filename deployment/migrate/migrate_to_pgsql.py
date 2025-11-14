#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SupaWriter 数据迁移脚本
将本地JSON数据迁移到PostgreSQL数据库

使用方法:
    python deployment/migrate/migrate_to_pgsql.py --host 122.51.24.120 --port 5432 --user supawriter --password YOUR_PASSWORD --database supawriter

或使用环境变量:
    export POSTGRES_HOST=122.51.24.120
    export POSTGRES_PORT=5432
    export POSTGRES_USER=supawriter
    export POSTGRES_PASSWORD=YOUR_PASSWORD
    export POSTGRES_DB=supawriter
    python deployment/migrate/migrate_to_pgsql.py
"""

import os
import json
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import Json, execute_values
from typing import List, Dict, Any, Optional

# 添加项目根目录到sys.path
# deployment/migrate/migrate_to_pgsql.py -> migrate/ -> deployment/ -> 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
HISTORY_DIR = os.path.join(DATA_DIR, 'history')
CONFIG_DIR = os.path.join(DATA_DIR, 'config')
CHAT_HISTORY_DIR = os.path.join(DATA_DIR, 'chat_history')


class PostgreSQLMigrator:
    """PostgreSQL数据迁移器"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        初始化迁移器
        
        Args:
            host: PostgreSQL服务器地址
            port: PostgreSQL端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None
        
    def connect(self) -> bool:
        """连接到PostgreSQL数据库"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.conn.cursor()
            logger.info(f"成功连接到PostgreSQL数据库 {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            logger.error(f"连接数据库失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("已断开数据库连接")
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            self.cursor.execute("SELECT version();")
            version = self.cursor.fetchone()
            logger.info(f"PostgreSQL版本: {version[0]}")
            return True
        except Exception as e:
            logger.error(f"测试连接失败: {str(e)}")
            return False
    
    def migrate_articles(self, username: str, articles: List[Dict[str, Any]]) -> int:
        """
        迁移文章数据
        
        Args:
            username: 用户名
            articles: 文章列表
            
        Returns:
            成功迁移的文章数量
        """
        if not articles:
            logger.info(f"用户 {username} 没有文章数据需要迁移")
            return 0
        
        success_count = 0
        for article in articles:
            try:
                # 准备文章数据
                topic = article.get('topic', '')
                article_content = article.get('article_content', '')
                summary = article.get('summary')
                
                # 处理tags字段：支持字符串和数组格式
                tags_raw = article.get('tags', [])
                if isinstance(tags_raw, str):
                    # 如果是逗号分隔的字符串，转换为列表
                    tags = [tag.strip() for tag in tags_raw.split(',') if tag.strip()]
                elif isinstance(tags_raw, list):
                    tags = tags_raw
                else:
                    tags = []
                
                model_type = article.get('model_type')
                model_name = article.get('model_name')
                write_type = article.get('write_type')
                spider_num = article.get('spider_num')
                custom_style = article.get('custom_style')
                is_transformed = article.get('is_transformed', False)
                image_task_id = article.get('image_task_id')
                image_enabled = article.get('image_enabled', False)
                image_similarity_threshold = article.get('image_similarity_threshold')
                image_max_count = article.get('image_max_count')
                article_topic = article.get('article_topic')
                
                # 构建metadata
                metadata = {
                    'original_id': article.get('id'),
                    'timestamp': article.get('timestamp')
                }
                
                # 解析创建时间
                timestamp_str = article.get('timestamp')
                created_at = None
                if timestamp_str:
                    try:
                        created_at = datetime.fromisoformat(timestamp_str)
                    except:
                        created_at = datetime.now()
                else:
                    created_at = datetime.now()
                
                # 插入文章
                insert_query = """
                INSERT INTO articles (
                    username, topic, article_content, summary, tags, metadata,
                    model_type, model_name, write_type, spider_num, custom_style,
                    is_transformed, image_task_id, image_enabled, 
                    image_similarity_threshold, image_max_count, article_topic,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
                """
                
                self.cursor.execute(insert_query, (
                    username, topic, article_content, summary, tags, Json(metadata),
                    model_type, model_name, write_type, spider_num, custom_style,
                    is_transformed, image_task_id, image_enabled,
                    image_similarity_threshold, image_max_count, article_topic,
                    created_at, created_at
                ))
                
                # 每次插入成功后立即提交，避免事务中止问题
                self.conn.commit()
                success_count += 1
                
            except Exception as e:
                # 发生错误时回滚当前事务
                self.conn.rollback()
                logger.error(f"迁移文章失败 (用户: {username}, 主题: {article.get('topic', 'Unknown')}): {str(e)}")
        
        logger.info(f"用户 {username} 迁移了 {success_count}/{len(articles)} 篇文章")
        return success_count
    
    def migrate_chat_sessions(self, username: str, sessions: List[Dict[str, Any]]) -> int:
        """
        迁移聊天会话数据
        
        Args:
            username: 用户名
            sessions: 聊天会话列表
            
        Returns:
            成功迁移的会话数量
        """
        if not sessions:
            logger.info(f"用户 {username} 没有聊天历史需要迁移")
            return 0
        
        success_count = 0
        for session in sessions:
            try:
                title = session.get('title', 'Untitled Chat')
                messages = session.get('messages', [])
                
                # 解析时间
                created_at_str = session.get('created_at')
                updated_at_str = session.get('updated_at')
                
                created_at = datetime.now()
                updated_at = datetime.now()
                
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                    except:
                        pass
                
                if updated_at_str:
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str)
                    except:
                        pass
                
                # 插入聊天会话
                insert_query = """
                INSERT INTO chat_sessions (
                    username, title, messages, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
                """
                
                self.cursor.execute(insert_query, (
                    username, title, Json(messages), created_at, updated_at
                ))
                
                # 每次插入成功后立即提交，避免事务中止问题
                self.conn.commit()
                success_count += 1
                
            except Exception as e:
                # 发生错误时回滚当前事务
                self.conn.rollback()
                logger.error(f"迁移聊天会话失败 (用户: {username}, 标题: {session.get('title', 'Unknown')}): {str(e)}")
        
        logger.info(f"用户 {username} 迁移了 {success_count}/{len(sessions)} 个聊天会话")
        return success_count
    
    def migrate_user_config(self, username: str, config: Dict[str, Any]) -> bool:
        """
        迁移用户配置数据
        
        Args:
            username: 用户名
            config: 配置数据
            
        Returns:
            是否成功
        """
        if not config:
            logger.info(f"用户 {username} 没有配置数据需要迁移")
            return False
        
        try:
            # 插入或更新用户配置
            insert_query = """
            INSERT INTO user_configs (username, config, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) 
            DO UPDATE SET 
                config = EXCLUDED.config,
                updated_at = EXCLUDED.updated_at
            """
            
            now = datetime.now()
            self.cursor.execute(insert_query, (
                username, Json(config), now, now
            ))
            
            self.conn.commit()
            logger.info(f"用户 {username} 配置迁移成功")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"迁移用户配置失败 (用户: {username}): {str(e)}")
            return False


def load_user_articles(username: str) -> List[Dict[str, Any]]:
    """加载用户的文章数据"""
    history_file = os.path.join(HISTORY_DIR, f"{username}_history.json")
    if not os.path.exists(history_file):
        return []
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载用户 {username} 文章数据失败: {str(e)}")
        return []


def load_user_chat_sessions(username: str) -> List[Dict[str, Any]]:
    """加载用户的聊天历史"""
    user_chat_dir = os.path.join(CHAT_HISTORY_DIR, username)
    if not os.path.exists(user_chat_dir):
        return []
    
    sessions = []
    for filename in os.listdir(user_chat_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(user_chat_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    sessions.append(session_data)
            except Exception as e:
                logger.error(f"加载聊天会话失败 {file_path}: {str(e)}")
    
    return sessions


def load_user_config(username: str) -> Dict[str, Any]:
    """加载用户配置"""
    config_file = os.path.join(CONFIG_DIR, f"{username}_config.json")
    if not os.path.exists(config_file):
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载用户 {username} 配置失败: {str(e)}")
        return {}


def get_all_usernames() -> List[str]:
    """获取所有用户名"""
    usernames = set()
    
    # 从历史文件获取用户名
    if os.path.exists(HISTORY_DIR):
        for filename in os.listdir(HISTORY_DIR):
            if filename.endswith('_history.json'):
                username = filename.replace('_history.json', '')
                usernames.add(username)
    
    # 从配置文件获取用户名
    if os.path.exists(CONFIG_DIR):
        for filename in os.listdir(CONFIG_DIR):
            if filename.endswith('_config.json'):
                username = filename.replace('_config.json', '')
                if username != 'default':  # 跳过默认配置
                    usernames.add(username)
    
    # 从聊天历史获取用户名
    if os.path.exists(CHAT_HISTORY_DIR):
        for dirname in os.listdir(CHAT_HISTORY_DIR):
            dir_path = os.path.join(CHAT_HISTORY_DIR, dirname)
            if os.path.isdir(dir_path):
                usernames.add(dirname)
    
    return list(usernames)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='将SupaWriter本地数据迁移到PostgreSQL')
    parser.add_argument('--host', type=str, default=os.getenv('POSTGRES_HOST', '122.51.24.120'),
                        help='PostgreSQL服务器地址')
    parser.add_argument('--port', type=int, default=int(os.getenv('POSTGRES_PORT', '5432')),
                        help='PostgreSQL端口')
    parser.add_argument('--user', type=str, default=os.getenv('POSTGRES_USER', 'supawriter'),
                        help='数据库用户名')
    parser.add_argument('--password', type=str, default=os.getenv('POSTGRES_PASSWORD', ''),
                        help='数据库密码')
    parser.add_argument('--database', type=str, default=os.getenv('POSTGRES_DB', 'supawriter'),
                        help='数据库名')
    parser.add_argument('--username', type=str, default=None,
                        help='仅迁移指定用户的数据（不指定则迁移所有用户）')
    parser.add_argument('--test', action='store_true',
                        help='仅测试数据库连接，不迁移数据')
    
    args = parser.parse_args()
    
    # 检查密码
    if not args.password:
        logger.error("错误: 未提供数据库密码")
        logger.error("请通过 --password 参数或 POSTGRES_PASSWORD 环境变量提供密码")
        return 1
    
    # 创建迁移器
    migrator = PostgreSQLMigrator(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )
    
    # 连接数据库
    if not migrator.connect():
        return 1
    
    # 测试连接
    if not migrator.test_connection():
        migrator.disconnect()
        return 1
    
    # 如果只是测试连接，则退出
    if args.test:
        logger.info("数据库连接测试成功！")
        migrator.disconnect()
        return 0
    
    # 获取要迁移的用户列表
    if args.username:
        usernames = [args.username]
    else:
        usernames = get_all_usernames()
    
    if not usernames:
        logger.warning("没有找到任何用户数据需要迁移")
        migrator.disconnect()
        return 0
    
    logger.info(f"找到 {len(usernames)} 个用户需要迁移: {', '.join(usernames)}")
    
    # 统计信息
    total_articles = 0
    total_sessions = 0
    total_configs = 0
    
    # 迁移每个用户的数据
    for username in usernames:
        logger.info(f"\n{'='*60}")
        logger.info(f"开始迁移用户: {username}")
        logger.info(f"{'='*60}")
        
        # 迁移文章
        articles = load_user_articles(username)
        articles_count = migrator.migrate_articles(username, articles)
        total_articles += articles_count
        
        # 迁移聊天历史
        sessions = load_user_chat_sessions(username)
        sessions_count = migrator.migrate_chat_sessions(username, sessions)
        total_sessions += sessions_count
        
        # 迁移配置
        config = load_user_config(username)
        if migrator.migrate_user_config(username, config):
            total_configs += 1
    
    # 输出总结
    logger.info(f"\n{'='*60}")
    logger.info("数据迁移完成！")
    logger.info(f"{'='*60}")
    logger.info(f"总计迁移:")
    logger.info(f"  - 用户数: {len(usernames)}")
    logger.info(f"  - 文章数: {total_articles}")
    logger.info(f"  - 聊天会话数: {total_sessions}")
    logger.info(f"  - 用户配置数: {total_configs}")
    
    # 断开连接
    migrator.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
