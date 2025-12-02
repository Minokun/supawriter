#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
执行SQL迁移文件并从pickle迁移现有用户数据
"""

import os
import sys
import psycopg2
import pickle
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_env_file():
    """从deployment/.env文件加载环境变量"""
    env_file = project_root / 'deployment' / '.env'
    
    if not env_file.exists():
        print(f"⚠️  未找到配置文件: {env_file}")
        print("ℹ️  请创建 deployment/.env 文件")
        print("ℹ️  使用默认配置或系统环境变量")
        return
    
    print(f"📄 加载配置文件: {env_file}")
    
    try:
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
                    
                    # 移除引号
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # 只有当环境变量不存在时才设置
                    if key and not os.getenv(key):
                        os.environ[key] = value
        
        print(f"✅ 配置文件加载成功")
        
    except Exception as e:
        print(f"⚠️  加载配置文件失败: {e}")


def get_database_connection():
    """获取数据库连接"""
    # 先加载.env文件
    load_env_file()
    
    # 从环境变量获取数据库配置
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # 从单独的环境变量构建
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'supawriter')
        user = os.getenv('POSTGRES_USER', 'supawriter')
        password = os.getenv('POSTGRES_PASSWORD', '')
        
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    print(f"\n📡 数据库连接信息:")
    # 解析URL显示信息（隐藏密码）
    try:
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        print(f"  主机: {parsed.hostname}")
        print(f"  端口: {parsed.port}")
        print(f"  数据库: {parsed.path.lstrip('/')}")
        print(f"  用户: {parsed.username}")
        print(f"  密码: {'*' * len(parsed.password) if parsed.password else '(未设置)'}")
    except:
        pass
    
    print(f"\n🔌 正在连接数据库...")
    
    try:
        conn = psycopg2.connect(database_url)
        print(f"✅ 成功连接到数据库")
        return conn
    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")
        print(f"\n💡 故障排查提示:")
        print(f"  1. 检查 deployment/.env 文件是否存在")
        print(f"  2. 确认数据库服务是否启动: docker-compose -f deployment/docker-compose.yml ps")
        print(f"  3. 检查数据库连接信息是否正确")
        print(f"  4. 如果使用Docker，确保POSTGRES_HOST设置正确（容器内用'postgres'，外部用'localhost'或IP）")
        sys.exit(1)


def run_migration_file(conn, migration_file):
    """执行单个迁移文件"""
    print(f"\n执行迁移文件: {migration_file}")
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        
        print(f"✅ 迁移文件执行成功: {migration_file}")
        return True
    except Exception as e:
        print(f"❌ 执行迁移文件失败: {e}")
        conn.rollback()
        return False


def migrate_pickle_users(conn):
    """从pickle文件迁移现有用户"""
    pickle_path = project_root / 'data' / 'users.pkl'
    
    if not pickle_path.exists():
        print("ℹ️  未找到pickle用户文件，跳过数据迁移")
        return True
    
    print(f"\n开始从pickle迁移用户数据: {pickle_path}")
    
    try:
        with open(pickle_path, 'rb') as f:
            users = pickle.load(f)
        
        cursor = conn.cursor()
        migrated_count = 0
        skipped_count = 0
        
        for username, user_obj in users.items():
            try:
                # 检查用户是否已存在
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    print(f"  ⏭️  用户已存在，跳过: {username}")
                    skipped_count += 1
                    continue
                
                # 插入用户
                cursor.execute("""
                    INSERT INTO users (
                        username, email, password_hash, display_name, 
                        motto, last_login, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_obj.username,
                    getattr(user_obj, 'email', None),
                    user_obj.password_hash,
                    username,  # 使用username作为display_name
                    getattr(user_obj, 'motto', '创作改变世界'),
                    getattr(user_obj, 'last_login', None),
                    getattr(user_obj, 'created_at', None)
                ))
                
                migrated_count += 1
                print(f"  ✅ 迁移用户: {username}")
                
            except Exception as e:
                print(f"  ❌ 迁移用户失败 {username}: {e}")
                continue
        
        conn.commit()
        cursor.close()
        
        print(f"\n✅ 用户迁移完成: 成功 {migrated_count} 个，跳过 {skipped_count} 个")
        
        # 备份原pickle文件
        backup_path = pickle_path.parent / f"{pickle_path.name}.backup"
        pickle_path.rename(backup_path)
        print(f"ℹ️  原pickle文件已备份到: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移pickle用户失败: {e}")
        conn.rollback()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("SupaWriter 数据库迁移工具")
    print("=" * 60)
    
    # 获取数据库连接
    conn = get_database_connection()
    
    # 执行所有迁移文件
    migration_dir = project_root / 'deployment' / 'migrate'
    migration_files = sorted(migration_dir.glob('*.sql'))
    
    if not migration_files:
        print("⚠️  未找到迁移文件")
    else:
        print(f"\n找到 {len(migration_files)} 个迁移文件")
        
        for migration_file in migration_files:
            if not run_migration_file(conn, migration_file):
                print(f"\n❌ 迁移失败，停止执行")
                conn.close()
                sys.exit(1)
    
    # 迁移pickle用户数据
    if not migrate_pickle_users(conn):
        print(f"\n⚠️  用户数据迁移失败")
    
    # 关闭连接
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 数据库迁移完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
