#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""执行数据库迁移脚本"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.database import Database

def run_migration(sql_file: str):
    """执行迁移脚本"""
    sql_path = project_root / sql_file
    if not sql_path.exists():
        print(f"❌ 迁移脚本不存在: {sql_path}")
        return False

    print(f"📄 读取迁移脚本: {sql_path}")
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    print("🔄 执行迁移...")
    try:
        with Database.get_cursor() as cursor:
            # 直接执行整个 SQL 文件
            cursor.execute(sql_content)

        print("✅ 迁移成功完成!")
        return True
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False

if __name__ == "__main__":
    migration_file = "deployment/migrate/007_create_llm_provider_templates.sql"
    print("=" * 50)
    print("LLM 提供商模板表迁移")
    print("=" * 50)

    if run_migration(migration_file):
        sys.exit(0)
    else:
        sys.exit(1)
