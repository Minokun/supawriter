#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清除数据库中的测试数据"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

# 从环境变量读取数据库连接信息
def get_db_connection():
    """获取数据库连接"""
    # 读取 deployment/.env 文件
    env_file = Path(__file__).parent.parent / "deployment" / ".env"
    
    db_config = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key == 'DATABASE_URL':
                        db_config['url'] = value
    
    if 'url' in db_config:
        # 解析 DATABASE_URL
        # 格式: postgresql://user:password@host:port/database
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_config['url'])
        if match:
            user, password, host, port, database = match.groups()
            return psycopg2.connect(
                host=host,
                port=int(port),
                database=database,
                user=user,
                password=password
            )
    
    raise Exception("无法从 deployment/.env 读取数据库配置")


def clear_all_data():
    """清除所有测试数据"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("开始清除数据库测试数据...")
        print("=" * 60)
        
        # 1. 查看当前数据
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        print(f"\n当前用户数量: {user_count}")
        
        cursor.execute("SELECT COUNT(*) as count FROM oauth_accounts")
        oauth_count = cursor.fetchone()['count']
        print(f"当前 OAuth 账号数量: {oauth_count}")
        
        # 2. 删除 OAuth 账号（外键关联）
        print("\n删除 OAuth 账号...")
        cursor.execute("DELETE FROM oauth_accounts")
        conn.commit()
        print(f"✅ 已删除 {cursor.rowcount} 条 OAuth 账号记录")
        
        # 3. 删除用户设置（如果有）
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE '%settings%' OR table_name LIKE '%config%')
            AND table_type = 'BASE TABLE'
            AND table_name NOT LIKE 'pg_%'
        """)
        settings_tables = cursor.fetchall()
        
        for table in settings_tables:
            table_name = table['table_name']
            print(f"\n删除 {table_name} 表数据...")
            try:
                cursor.execute(f"DELETE FROM {table_name}")
                conn.commit()
                print(f"✅ 已删除 {cursor.rowcount} 条记录")
            except Exception as e:
                print(f"⚠️  跳过 {table_name}: {e}")
                conn.rollback()
        
        # 4. 删除聊天会话和消息（如果有）
        for table_name in ['chat_messages', 'chat_sessions']:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table_name}'
                )
            """)
            if cursor.fetchone()['exists']:
                print(f"\n删除 {table_name} 表数据...")
                cursor.execute(f"DELETE FROM {table_name}")
                conn.commit()
                print(f"✅ 已删除 {cursor.rowcount} 条记录")
        
        # 5. 删除所有用户
        print("\n删除所有用户...")
        cursor.execute("DELETE FROM users")
        conn.commit()
        print(f"✅ 已删除 {cursor.rowcount} 条用户记录")
        
        # 6. 重置序列（自增 ID）
        print("\n重置自增序列...")
        cursor.execute("ALTER SEQUENCE users_id_seq RESTART WITH 1")
        cursor.execute("ALTER SEQUENCE oauth_accounts_id_seq RESTART WITH 1")
        conn.commit()
        print("✅ 已重置序列")
        
        # 7. 验证清理结果
        print("\n" + "=" * 60)
        print("验证清理结果:")
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        print(f"用户数量: {user_count}")
        
        cursor.execute("SELECT COUNT(*) as count FROM oauth_accounts")
        oauth_count = cursor.fetchone()['count']
        print(f"OAuth 账号数量: {oauth_count}")
        
        print("\n✅ 数据库清理完成！")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    try:
        clear_all_data()
    except Exception as e:
        print(f"\n清理失败: {e}")
        sys.exit(1)
