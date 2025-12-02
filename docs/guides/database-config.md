# 数据库配置指南

## 问题说明

你遇到的错误是因为迁移脚本无法连接到数据库。有两种情况：

### 情况1：使用本地Docker数据库

**配置文件**: `.env.local`（项目根目录）

```bash
# 本地Docker配置
POSTGRES_PASSWORD=^1234qwerasdf$
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=supawriter
POSTGRES_USER=supawriter
DATABASE_URL=postgresql://supawriter:^1234qwerasdf$@localhost:5432/supawriter
```

**启动数据库**:
```bash
cd deployment
docker-compose up -d postgres
docker-compose ps  # 确认容器运行中
```

### 情况2：使用远程服务器数据库

**配置文件**: `.env.local`（项目根目录）

```bash
# 远程服务器配置
POSTGRES_PASSWORD=^1234qwerasdf$
POSTGRES_HOST=122.51.24.120  # 改为你的服务器IP
POSTGRES_PORT=5432
POSTGRES_DB=supawriter
POSTGRES_USER=supawriter
DATABASE_URL=postgresql://supawriter:^1234qwerasdf$@122.51.24.120:5432/supawriter
```

## 快速修复步骤

### 选项A：使用本地Docker（推荐）

```bash
# 1. 启动数据库
cd /Users/wxk/Desktop/workspace/supawriter/deployment
docker-compose up -d postgres

# 2. 等待启动
sleep 10

# 3. 验证运行
docker-compose ps

# 4. 运行迁移
cd ..
python scripts/migrate_database.py
```

### 选项B：连接远程服务器

```bash
# 1. 编辑 .env.local
nano .env.local

# 修改 POSTGRES_HOST=122.51.24.120
# 保存后退出 (Ctrl+X, Y, Enter)

# 2. 测试连接
psql -h 122.51.24.120 -p 5432 -U supawriter -d supawriter

# 3. 运行迁移
python scripts/migrate_database.py
```

## 我已经做了什么

✅ 修复了 `scripts/migrate_database.py`，现在会自动读取配置：
   - 优先读取 `.env.local`（本地开发）
   - 其次读取 `deployment/.env`（Docker）

✅ 创建了 `.env.local` 模板文件（已配置为localhost）

## 下一步

请选择你的情况并执行对应的命令！
