#!/usr/bin/env python3
"""给 articles 表添加 user_id 字段"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.database import Database

def add_user_id_column():
    """给 articles 表添加 user_id 字段并迁移数据"""
    
    print("🔧 开始修复 articles 表...")
    
    try:
        with Database.get_cursor() as cursor:
            # 1. 检查 user_id 字段是否已存在
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'articles' AND column_name = 'user_id'
            """)
            
            if cursor.fetchone():
                print("✅ user_id 字段已存在，无需添加")
                return True
            
            print("\n📝 步骤 1: 添加 user_id 字段...")
            
            # 2. 添加 user_id 字段（先允许 NULL）
            cursor.execute("""
                ALTER TABLE articles 
                ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            """)
            print("   ✅ user_id 字段已添加")
            
            # 3. 从 username 迁移数据到 user_id
            print("\n📝 步骤 2: 迁移现有数据...")
            cursor.execute("""
                UPDATE articles a
                SET user_id = u.id
                FROM users u
                WHERE a.username = u.username
            """)
            
            rows_updated = cursor.rowcount
            print(f"   ✅ 已更新 {rows_updated} 条记录")
            
            # 4. 检查是否有未匹配的记录
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM articles
                WHERE user_id IS NULL
            """)
            
            null_count = cursor.fetchone()['count']
            
            if null_count > 0:
                print(f"\n   ⚠️  警告: 有 {null_count} 条记录的 username 在 users 表中不存在")
                print("   这些记录将被设置为 admin 用户")
                
                # 获取 admin 用户 ID
                cursor.execute("SELECT id FROM users WHERE username = 'admin'")
                admin_user = cursor.fetchone()
                
                if admin_user:
                    cursor.execute("""
                        UPDATE articles
                        SET user_id = %s
                        WHERE user_id IS NULL
                    """, (admin_user['id'],))
                    print(f"   ✅ 已将 {null_count} 条记录设置为 admin 用户")
            
            # 5. 设置 user_id 为 NOT NULL
            print("\n📝 步骤 3: 设置 user_id 为必填字段...")
            cursor.execute("""
                ALTER TABLE articles 
                ALTER COLUMN user_id SET NOT NULL
            """)
            print("   ✅ user_id 已设置为 NOT NULL")
            
            # 6. 创建索引
            print("\n📝 步骤 4: 创建索引...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_user_id 
                ON articles(user_id)
            """)
            print("   ✅ 索引已创建")
            
            # 7. 验证结果
            print("\n📝 步骤 5: 验证结果...")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT user_id) as unique_users
                FROM articles
            """)
            
            stats = cursor.fetchone()
            print(f"   ✅ 总文章数: {stats['total']}")
            print(f"   ✅ 用户数: {stats['unique_users']}")
            
            print("\n✅ articles 表修复完成!")
            return True
            
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = add_user_id_column()
    sys.exit(0 if success else 1)
