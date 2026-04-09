#!/usr/bin/env python3
"""检查 articles 表结构"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.database import Database

def check_articles_table():
    """检查 articles 表的结构和数据"""
    
    print("📊 检查 articles 表结构...")
    
    try:
        with Database.get_cursor() as cursor:
            # 1. 查看表结构
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'articles'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            
            print("\n✅ articles 表字段:")
            print("=" * 80)
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  {col['column_name']:30} {col['data_type']:20} {nullable:10} {default}")
            
            # 2. 查看现有数据
            cursor.execute("""
                SELECT id, username, topic, created_at
                FROM articles
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            articles = cursor.fetchall()
            
            print("\n📝 最近的文章记录:")
            print("=" * 80)
            if articles:
                for i, article in enumerate(articles, 1):
                    print(f"\n  {i}. ID: {article['id']}")
                    print(f"     用户: {article.get('username', 'N/A')}")
                    print(f"     标题: {article['topic']}")
                    print(f"     创建时间: {article['created_at']}")
            else:
                print("  ❌ 没有找到任何文章记录")
            
            # 3. 检查是否有 user_id 字段
            has_user_id = any(col['column_name'] == 'user_id' for col in columns)
            has_username = any(col['column_name'] == 'username' for col in columns)
            
            print("\n🔍 字段检查:")
            print("=" * 80)
            print(f"  user_id 字段: {'✅ 存在' if has_user_id else '❌ 不存在'}")
            print(f"  username 字段: {'✅ 存在' if has_username else '❌ 不存在'}")
            
            if not has_user_id:
                print("\n⚠️  警告: articles 表缺少 user_id 字段!")
                print("   后端 API 需要 user_id 字段来关联用户")
                return False
            
            return True
            
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = check_articles_table()
    sys.exit(0 if success else 1)
