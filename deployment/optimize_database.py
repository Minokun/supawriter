#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库性能优化脚本
执行索引创建和查询优化
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration(migration_file: str):
    """运行数据库迁移"""
    logger.info(f"执行迁移: {migration_file}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    with Database.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            conn.commit()
            logger.info(f"✅ 迁移成功: {migration_file}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ 迁移失败: {e}")
            return False


def check_indexes():
    """检查已创建的索引"""
    logger.info("\n检查数据库索引...")
    
    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """)
        
        indexes = cursor.fetchall()
        
        # 按表分组
        tables = {}
        for idx in indexes:
            table = idx['tablename']
            if table not in tables:
                tables[table] = []
            tables[table].append(idx['indexname'])
        
        logger.info(f"\n📊 索引统计:")
        for table, idx_list in sorted(tables.items()):
            logger.info(f"  {table}: {len(idx_list)} 个索引")
            for idx_name in idx_list:
                logger.info(f"    - {idx_name}")


def analyze_query_performance():
    """分析查询性能"""
    logger.info("\n分析查询性能...")
    
    queries = [
        ("用户文章列表", """
            EXPLAIN ANALYZE
            SELECT id, topic, status, created_at
            FROM articles
            WHERE user_id = 1
            ORDER BY created_at DESC
            LIMIT 20
        """),
        ("API 密钥查询", """
            EXPLAIN ANALYZE
            SELECT provider, is_active, created_at
            FROM user_api_keys
            WHERE user_id = 1 AND is_active = true
        """),
        ("聊天消息查询", """
            EXPLAIN ANALYZE
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = '00000000-0000-0000-0000-000000000001'
            ORDER BY created_at
            LIMIT 50
        """)
    ]
    
    with Database.get_cursor() as cursor:
        for name, query in queries:
            logger.info(f"\n🔍 {name}:")
            try:
                cursor.execute(query)
                results = cursor.fetchall()
                
                # 提取执行时间
                for row in results:
                    line = str(row)
                    if 'Execution Time' in line or 'Planning Time' in line:
                        logger.info(f"  {line}")
            except Exception as e:
                logger.warning(f"  查询失败: {e}")


def vacuum_analyze():
    """执行 VACUUM ANALYZE 优化"""
    logger.info("\n执行 VACUUM ANALYZE...")
    
    tables = [
        'users', 'articles', 'chat_sessions', 'chat_messages',
        'user_api_keys', 'user_model_configs', 'user_preferences'
    ]
    
    with Database.get_connection() as conn:
        conn.autocommit = True
        cursor = conn.cursor()
        
        for table in tables:
            try:
                logger.info(f"  优化表: {table}")
                cursor.execute(f"VACUUM ANALYZE {table}")
                logger.info(f"  ✅ {table} 优化完成")
            except Exception as e:
                logger.error(f"  ❌ {table} 优化失败: {e}")


def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("数据库性能优化")
    print("🚀 " * 30 + "\n")
    
    # 1. 运行索引迁移
    migration_file = os.path.join(
        os.path.dirname(__file__),
        'postgres/migrations/011_add_performance_indexes.sql'
    )
    
    if os.path.exists(migration_file):
        run_migration(migration_file)
    else:
        logger.warning(f"迁移文件不存在: {migration_file}")
    
    # 2. 检查索引
    check_indexes()
    
    # 3. 执行 VACUUM ANALYZE
    vacuum_analyze()
    
    # 4. 分析查询性能
    analyze_query_performance()
    
    print("\n" + "✅ " * 30)
    print("数据库优化完成")
    print("✅ " * 30 + "\n")


if __name__ == "__main__":
    main()
