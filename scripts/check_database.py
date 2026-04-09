#!/usr/bin/env python3
"""检查数据库表结构"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.database import Database

def check_tables():
    """检查数据库中的表"""
    try:
        with Database.get_cursor() as cursor:
            # 查询所有表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            print("📊 数据库中的表：")
            print("=" * 50)
            if tables:
                for table in tables:
                    print(f"  ✓ {table['table_name']}")
            else:
                print("  ❌ 没有找到任何表！")
            
            print("\n" + "=" * 50)
            print(f"总共 {len(tables)} 个表")
            
            # 检查关键表
            required_tables = [
                'users', 'oauth_accounts', 'articles', 
                'chat_sessions', 'chat_messages',
                'user_api_keys', 'user_model_configs'
            ]
            
            existing_table_names = [t['table_name'] for t in tables]
            missing_tables = [t for t in required_tables if t not in existing_table_names]
            
            if missing_tables:
                print("\n⚠️  缺少以下关键表：")
                for table in missing_tables:
                    print(f"  ❌ {table}")
                return False
            else:
                print("\n✅ 所有关键表都存在！")
                return True
                
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = check_tables()
    sys.exit(0 if success else 1)
