#!/usr/bin/env python3
"""应用完整的数据库初始化脚本"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.database import Database

def apply_init():
    """应用完整的数据库初始化"""
    sql_file = project_root / 'deployment/postgres/init/complete-init.sql'
    
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return False
    
    print("📖 读取完整初始化SQL文件...")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print("🔧 应用数据库初始化...")
    print("   这将创建缺失的表和索引...")
    
    try:
        with Database.get_cursor() as cursor:
            cursor.execute(sql_content)
        print("\n✅ 数据库初始化成功！")
        print("\n验证表结构...")
        
        # 验证关键表
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            print(f"\n当前数据库中的表 ({len(tables)} 个):")
            for table in tables:
                print(f"  ✓ {table['table_name']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = apply_init()
    sys.exit(0 if success else 1)
