# SupaWriter 数据库迁移指南

## 📋 概述

本指南整合了所有数据库相关的迁移操作，包括：
- 全新部署（Docker）
- 现有数据库升级
- 历史数据迁移

## 🗂️ 文件说明

### SQL脚本文件

| 文件 | 用途 | 何时使用 |
|------|------|---------|
| `postgres/init/00-init-complete.sql` | ⭐ **完整初始化脚本**（推荐） | Docker全新部署 |
| `postgres/init/01-init.sql` | 旧的初始化脚本 | ⚠️ 已废弃，请使用上面的 |
| `migrate/001_create_auth_tables.sql` | 认证表单独脚本 | 手动升级现有数据库 |

### Python迁移脚本

| 脚本 | 用途 |
|------|------|
| `scripts/migrate_database.py` | 执行SQL迁移 + 迁移pickle用户数据 |
| `deployment/migrate/migrate_to_pgsql.py` | 迁移历史JSON文章数据 |
| `scripts/create_user.py` | 手动创建用户工具 |

## 🚀 迁移方案选择

### 方案一：全新部署（Docker）✨ 推荐

适用于：
- ✅ 第一次部署SupaWriter
- ✅ 想使用Docker容器
- ✅ 没有历史数据需要迁移

#### 步骤：

```bash
# 1. 进入deployment目录
cd deployment

# 2. 配置环境变量
cp .env.example .env
# 编辑.env，设置数据库密码等

# 3. 启动PostgreSQL容器
docker-compose up -d postgres

# 4. 等待数据库初始化完成（约10-30秒）
docker-compose logs -f postgres
# 看到 "database system is ready to accept connections" 即可

# 5. 验证数据库
docker exec -it supawriter_postgres psql -U supawriter -d supawriter -c "\dt"
```

**初始化内容：**
- ✅ 创建所有表（users, oauth_accounts, articles, chat_sessions, user_configs）
- ✅ 创建索引和触发器
- ✅ 创建默认管理员账号（admin/admin123）

---

### 方案二：现有数据库升级

适用于：
- ✅ 已有运行中的PostgreSQL
- ✅ 需要添加认证系统表
- ✅ 保留现有articles等数据

#### 步骤：

```bash
# 1. 备份现有数据库（重要！）
pg_dump -h localhost -U supawriter -d supawriter > backup_$(date +%Y%m%d).sql

# 2. 检查现有表
psql -h localhost -U supawriter -d supawriter -c "\dt"

# 3. 执行认证系统迁移
cd /Users/wxk/Desktop/workspace/supawriter
python scripts/migrate_database.py

# 或者手动执行SQL
psql -h localhost -U supawriter -d supawriter -f deployment/migrate/001_create_auth_tables.sql

# 4. 验证新表
psql -h localhost -U supawriter -d supawriter -c "SELECT * FROM users;"
```

**会创建：**
- ✅ users表
- ✅ oauth_accounts表
- ✅ 相关索引和触发器
- ✅ 默认管理员账号

---

### 方案三：迁移历史数据

适用于：
- ✅ 有历史JSON文章数据
- ✅ 有旧的pickle用户数据
- ✅ 需要导入到PostgreSQL

#### 3.1 迁移用户数据（从pickle）

```bash
# 数据源：data/users.pkl
cd /Users/wxk/Desktop/workspace/supawriter

# 执行迁移（已包含在migrate_database.py中）
python scripts/migrate_database.py
```

**迁移内容：**
- ✅ 用户名、邮箱、密码哈希
- ✅ 创建时间、最后登录时间
- ✅ 座右铭等自定义字段

#### 3.2 迁移文章数据（从JSON）

```bash
# 数据源：data/history/*.json
cd deployment/migrate

# 配置数据库连接
cp .env.migration.example .env.migration
# 编辑.env.migration

# 执行迁移
python migrate_to_pgsql.py
```

**迁移内容：**
- ✅ 文章内容、标题、摘要
- ✅ 聊天会话历史
- ✅ 用户配置

---

## 📝 详细操作步骤

### Docker全新部署（完整流程）

```bash
# ==========================================
# 第1步：准备工作
# ==========================================

cd /Users/wxk/Desktop/workspace/supawriter/deployment

# 配置环境变量
cat > .env << 'EOF'
POSTGRES_PASSWORD=YourStrongPassword123!
PGADMIN_PASSWORD=YourStrongPassword123!
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=supawriter
POSTGRES_USER=supawriter
DATABASE_URL=postgresql://supawriter:YourStrongPassword123!@postgres:5432/supawriter
EOF

# ==========================================
# 第2步：启动数据库
# ==========================================

# 启动PostgreSQL
docker-compose up -d postgres

# 查看日志，确认初始化完成
docker-compose logs -f postgres
# 等待出现: "PostgreSQL init process complete; ready for start up"
# Ctrl+C退出日志

# ==========================================
# 第3步：验证部署
# ==========================================

# 连接数据库
docker exec -it supawriter_postgres psql -U supawriter -d supawriter

# 在psql中执行：
\dt                    # 查看所有表
SELECT * FROM users;   # 查看用户表
\q                     # 退出

# ==========================================
# 第4步：测试登录
# ==========================================

# 安装Python依赖
cd ..
pip install psycopg2-binary

# 测试认证系统
python scripts/test_auth_system.py

# 启动应用
streamlit run web.py
# 使用 admin/admin123 登录
```

---

### 现有数据库升级（完整流程）

```bash
# ==========================================
# 第1步：备份数据库
# ==========================================

# 创建备份
pg_dump -h localhost -U supawriter -d supawriter -F c -f backup_$(date +%Y%m%d_%H%M%S).dump

# 或导出为SQL
pg_dump -h localhost -U supawriter -d supawriter > backup_$(date +%Y%m%d_%H%M%S).sql

# ==========================================
# 第2步：检查数据库状态
# ==========================================

psql -h localhost -U supawriter -d supawriter -c "
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
"

# ==========================================
# 第3步：执行迁移
# ==========================================

cd /Users/wxk/Desktop/workspace/supawriter

# 确保.env配置正确
cat deployment/.env

# 执行迁移脚本
python scripts/migrate_database.py

# ==========================================
# 第4步：验证迁移结果
# ==========================================

# 检查新表
psql -h localhost -U supawriter -d supawriter -c "
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('users', 'oauth_accounts')
ORDER BY table_name, ordinal_position;
"

# 查看管理员账号
psql -h localhost -U supawriter -d supawriter -c "
SELECT id, username, email, is_superuser, created_at 
FROM users 
WHERE username = 'admin';
"

# ==========================================
# 第5步：测试应用
# ==========================================

# 运行测试
python scripts/test_auth_system.py

# 启动应用测试登录
streamlit run web.py
```

---

## 🔄 数据迁移详细步骤

### 迁移用户数据（pickle → PostgreSQL）

```bash
# 1. 检查pickle文件
ls -lh data/users.pkl

# 2. 查看pickle内容（可选）
python -c "
import pickle
with open('data/users.pkl', 'rb') as f:
    users = pickle.load(f)
    print(f'用户数量: {len(users)}')
    for username in list(users.keys())[:5]:
        print(f'  - {username}')
"

# 3. 执行迁移
python scripts/migrate_database.py

# 4. 验证迁移结果
psql -h localhost -U supawriter -d supawriter -c "
SELECT username, email, created_at 
FROM users 
WHERE username != 'admin' 
ORDER BY created_at DESC 
LIMIT 10;
"
```

### 迁移文章数据（JSON → PostgreSQL）

```bash
# 1. 检查JSON文件
ls -lh data/history/

# 2. 配置迁移环境
cd deployment/migrate
cp .env.migration.example .env.migration

# 编辑.env.migration
nano .env.migration
# 填入数据库连接信息

# 3. 执行迁移
python migrate_to_pgsql.py

# 4. 验证迁移结果
psql -h localhost -U supawriter -d supawriter -c "
SELECT 
    username,
    COUNT(*) as article_count,
    MAX(created_at) as last_article
FROM articles 
GROUP BY username;
"
```

---

## 🛠️ 故障排查

### 问题1：Docker容器无法启动

```bash
# 检查端口占用
lsof -i :5432

# 查看容器日志
docker-compose logs postgres

# 重新启动
docker-compose down
docker-compose up -d postgres
```

### 问题2：数据库连接失败

```bash
# 测试连接
psql -h localhost -p 5432 -U supawriter -d supawriter

# 检查环境变量
cat deployment/.env

# 检查pg_hba.conf
docker exec supawriter_postgres cat /etc/postgresql/pg_hba.conf
```

### 问题3：表已存在错误

```bash
# 方案A：删除旧表（谨慎！）
psql -h localhost -U supawriter -d supawriter -c "
DROP TABLE IF EXISTS oauth_accounts CASCADE;
DROP TABLE IF EXISTS users CASCADE;
"

# 方案B：使用新的数据库
createdb -h localhost -U supawriter supawriter_new
```

### 问题4：迁移脚本失败

```bash
# 查看详细错误
python scripts/migrate_database.py 2>&1 | tee migration.log

# 手动执行SQL
psql -h localhost -U supawriter -d supawriter -f deployment/migrate/001_create_auth_tables.sql
```

---

## 📊 迁移后验证清单

### ✅ 数据库结构验证

```bash
# 1. 检查所有表
psql -h localhost -U supawriter -d supawriter -c "\dt"

# 应该看到:
# - users
# - oauth_accounts
# - articles
# - chat_sessions
# - user_configs

# 2. 检查索引
psql -h localhost -U supawriter -d supawriter -c "\di"

# 3. 检查触发器
psql -h localhost -U supawriter -d supawriter -c "
SELECT trigger_name, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 'public';
"
```

### ✅ 数据验证

```bash
# 1. 用户数据
psql -h localhost -U supawriter -d supawriter -c "
SELECT COUNT(*) as user_count FROM users;
"

# 2. 文章数据
psql -h localhost -U supawriter -d supawriter -c "
SELECT COUNT(*) as article_count FROM articles;
"

# 3. 聊天会话
psql -h localhost -U supawriter -d supawriter -c "
SELECT COUNT(*) as session_count FROM chat_sessions;
"
```

### ✅ 功能验证

```bash
# 1. 运行测试套件
python scripts/test_auth_system.py

# 2. 测试登录
streamlit run web.py
# 访问 http://localhost:8501
# 使用 admin/admin123 登录

# 3. 测试账号创建
python scripts/create_user.py \
    --username testuser \
    --email test@example.com \
    --password Test123456!
```

---

## 📚 相关文档

- [认证系统V2指南](../AUTHENTICATION_V2_GUIDE.md)
- [快速开始指南](../QUICKSTART_AUTH_V2.md)
- [注册策略说明](../REGISTRATION_POLICY.md)
- [Docker部署文档](README.md)

---

## 💡 最佳实践

1. **始终备份** - 在执行任何迁移前备份数据库
2. **测试环境** - 先在测试环境验证迁移脚本
3. **分步执行** - 按步骤执行，每步验证结果
4. **保留日志** - 记录迁移过程和错误信息
5. **修改密码** - 迁移后立即修改默认管理员密码

---

## 🆘 获取帮助

如遇问题：
1. 查看本文档的故障排查部分
2. 检查应用日志和数据库日志
3. 运行测试脚本诊断问题
4. 联系技术支持：952718180@qq.com
