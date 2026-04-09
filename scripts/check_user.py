#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查特定用户"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """获取数据库连接"""
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


def check_user(email):
    """检查用户信息"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print(f"检查用户: {email}")
        print("=" * 60)
        
        # 查询用户
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            print("\n✅ 用户存在")
            print(f"ID: {user['id']}")
            print(f"用户名: {user['username']}")
            print(f"邮箱: {user['email']}")
            print(f"显示名称: {user['display_name']}")
            print(f"有密码: {user['password_hash'] is not None}")
            print(f"创建时间: {user['created_at']}")
            print(f"最后登录: {user['last_login']}")
            
            # 查询 OAuth 账号
            cursor.execute("""
                SELECT * FROM oauth_accounts 
                WHERE user_id = %s
            """, (user['id'],))
            oauth_accounts = cursor.fetchall()
            
            print(f"\nOAuth 账号数量: {len(oauth_accounts)}")
            for account in oauth_accounts:
                print(f"  - {account['provider']}: {account['provider_user_id']}")
                print(f"    创建时间: {account['created_at']}")
        else:
            print("\n❌ 用户不存在")
            
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "wxk952718180@gmail.com"
    check_user(email)
