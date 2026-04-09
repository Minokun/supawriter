# 数据库初始化使用指南

## 📋 概述

本指南说明如何使用完整的数据库初始化SQL文件来创建或重建 SupaWriter 数据库。

---

## 🎯 快速开始

### 方法一：使用 psql 命令行

```bash
# 1. 连接到 PostgreSQL
psql -U postgres

# 2. 创建数据库（如果不存在）
CREATE DATABASE supawriter;

# 3. 退出并执行初始化脚本
\q
psql -U postgres -d supawriter -f deployment/postgres/init/complete-init.sql
```

### 方法二：使用 Python 脚本

创建一个初始化脚本 `scripts/init_database.py`:

```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.database import Database

def init_database():
    """初始化数据库"""
    sql_file = project_root / 'deployment/postgres/init/complete-init.sql'
    
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return False
    
    print("📖 读取SQL文件...")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print("🔧 执行数据库初始化...")
    try:
        with Database.get_cursor() as cursor:
            cursor.execute(sql_content)
        print("✅ 数据库初始化成功！")
        return True
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
```

运行：
```bash
uv run python scripts/init_database.py
```

### 方法三：使用 Docker

如果使用 Docker 部署：

```bash
# 将 SQL 文件复制到 Docker 容器
docker cp deployment/postgres/init/complete-init.sql postgres_container:/tmp/

# 在容器内执行
docker exec -it postgres_container psql -U postgres -d supawriter -f /tmp/complete-init.sql
```

---

## 🔄 重建数据库

### ⚠️ 警告：此操作会删除所有数据！

```bash
# 1. 删除现有数据库
psql -U postgres -c "DROP DATABASE IF EXISTS supawriter;"

# 2. 创建新数据库
psql -U postgres -c "CREATE DATABASE supawriter;"

# 3. 执行初始化脚本
psql -U postgres -d supawriter -f deployment/postgres/init/complete-init.sql
```

### 使用脚本重建

创建 `scripts/rebuild_database.sh`:

```bash
#!/bin/bash
set -e

echo "⚠️  警告：此操作将删除所有数据！"
read -p "确认继续？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ 操作已取消"
    exit 1
fi

echo "🗑️  删除现有数据库..."
psql -U postgres -c "DROP DATABASE IF EXISTS supawriter;"

echo "📦 创建新数据库..."
psql -U postgres -c "CREATE DATABASE supawriter;"

echo "🔧 执行初始化脚本..."
psql -U postgres -d supawriter -f deployment/postgres/init/complete-init.sql

echo "✅ 数据库重建完成！"
```

---

## 🔍 验证初始化

### 检查表是否创建成功

```sql
-- 连接到数据库
psql -U postgres -d supawriter

-- 查看所有表
\dt

-- 应该看到以下表：
-- users, oauth_accounts, articles, chat_sessions, chat_messages,
-- user_configs, user_api_keys, user_model_configs, user_preferences,
-- llm_providers, user_service_configs, system_settings
```

### 检查默认管理员账号

```sql
SELECT username, email, is_superuser, created_at 
FROM users 
WHERE username = 'admin';
```

应该返回：
```
 username |         email          | is_superuser |         created_at         
----------+------------------------+--------------+----------------------------
 admin    | admin@supawriter.com   | t            | 2026-02-02 14:50:00.123456
```

### 检查索引

```sql
-- 查看所有索引
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename, indexname;
```

### 检查视图

```sql
-- 查看所有视图
\dv

-- 测试视图
SELECT * FROM user_profile_view WHERE username = 'admin';
SELECT * FROM article_stats LIMIT 5;
```

---

## 🛠️ 常见问题

### Q1: 权限不足错误

```
ERROR: permission denied to create database
```

**解决方案**：
```bash
# 使用超级用户连接
psql -U postgres

# 或授予权限
GRANT CREATE ON DATABASE supawriter TO your_user;
```

### Q2: 数据库已存在

```
ERROR: database "supawriter" already exists
```

**解决方案**：
```bash
# 删除现有数据库（⚠️ 会丢失数据）
psql -U postgres -c "DROP DATABASE supawriter;"

# 或使用不同的数据库名
psql -U postgres -c "CREATE DATABASE supawriter_new;"
```

### Q3: 扩展安装失败

```
ERROR: could not open extension control file
```

**解决方案**：
```bash
# 安装 PostgreSQL 扩展包
# Ubuntu/Debian
sudo apt-get install postgresql-contrib

# macOS
brew install postgresql@14
```

### Q4: 连接被拒绝

```
psql: error: connection to server on socket failed
```

**解决方案**：
```bash
# 检查 PostgreSQL 是否运行
pg_isready

# 启动 PostgreSQL
# macOS
brew services start postgresql@14

# Linux
sudo systemctl start postgresql
```

---

## 📊 数据库配置

### 环境变量

确保 `.env` 文件包含正确的数据库连接信息：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/supawriter
```

### 连接池配置

在 `utils/database.py` 中配置连接池：

```python
connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    dsn=database_url
)
```

---

## 🔐 安全建议

### 1. 修改默认管理员密码

```sql
-- 生成新密码的哈希（使用 SHA256）
-- 在 Python 中：
-- import hashlib
-- hashlib.sha256('your_new_password'.encode()).hexdigest()

UPDATE users 
SET password_hash = 'your_new_password_hash'
WHERE username = 'admin';
```

### 2. 限制数据库访问

```sql
-- 创建应用专用用户
CREATE USER supawriter_app WITH PASSWORD 'strong_password';

-- 授予必要权限
GRANT CONNECT ON DATABASE supawriter TO supawriter_app;
GRANT USAGE ON SCHEMA public TO supawriter_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO supawriter_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO supawriter_app;
```

### 3. 启用 SSL 连接

在生产环境中，修改连接字符串：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/supawriter?sslmode=require
```

---

## 📈 性能优化

### 定期维护

```sql
-- 分析表（更新统计信息）
ANALYZE;

-- 清理死元组
VACUUM;

-- 完整清理和分析
VACUUM ANALYZE;
```

### 监控查询性能

```sql
-- 启用慢查询日志
ALTER DATABASE supawriter SET log_min_duration_statement = 1000;

-- 查看慢查询
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

---

## 🔄 备份与恢复

### 备份数据库

```bash
# 完整备份
pg_dump -U postgres supawriter > backup_$(date +%Y%m%d).sql

# 仅备份数据（不含结构）
pg_dump -U postgres --data-only supawriter > data_backup.sql

# 仅备份结构（不含数据）
pg_dump -U postgres --schema-only supawriter > schema_backup.sql
```

### 恢复数据库

```bash
# 从备份恢复
psql -U postgres -d supawriter < backup_20260202.sql

# 或使用 pg_restore（如果是自定义格式）
pg_restore -U postgres -d supawriter backup.dump
```

---

## 📝 迁移脚本

如果需要从旧版本迁移，可以使用以下步骤：

### 1. 备份现有数据

```bash
pg_dump -U postgres supawriter > old_database_backup.sql
```

### 2. 导出数据

```sql
-- 导出用户数据
COPY users TO '/tmp/users.csv' CSV HEADER;

-- 导出文章数据
COPY articles TO '/tmp/articles.csv' CSV HEADER;
```

### 3. 重建数据库

```bash
psql -U postgres -d supawriter -f deployment/postgres/init/complete-init.sql
```

### 4. 导入数据

```sql
-- 导入用户数据
COPY users FROM '/tmp/users.csv' CSV HEADER;

-- 导入文章数据
COPY articles FROM '/tmp/articles.csv' CSV HEADER;
```

---

## 📚 相关文档

- [数据库架构文档](DATABASE_SCHEMA.md)
- [部署指南](../deployment/frontend-backend-deployment.md)
- [API 文档](../api/README.md)

---

## 🆘 获取帮助

如果遇到问题：

1. 查看 PostgreSQL 日志
   ```bash
   # macOS
   tail -f /usr/local/var/log/postgres.log
   
   # Linux
   tail -f /var/log/postgresql/postgresql-14-main.log
   ```

2. 检查数据库连接
   ```bash
   psql -U postgres -d supawriter -c "SELECT version();"
   ```

3. 查看错误详情
   ```sql
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   ```

---

**维护者**: SupaWriter Team  
**最后更新**: 2026-02-02
