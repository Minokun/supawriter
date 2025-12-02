# SupaWriter 数据迁移指南

本指南介绍如何将本地JSON数据迁移到服务器的PostgreSQL数据库。

## 📋 准备工作

### 1. 确认服务器信息

从 `deployment/README.md` 中确认以下信息：
- **服务器地址**: `122.51.24.120`
- **数据库端口**: `5432`
- **数据库名**: `supawriter`
- **用户名**: `supawriter`
- **密码**: 在服务器的 `/opt/supawriter/.env` 文件中查看

### 2. 获取数据库密码

登录服务器查看密码：

```bash
# 登录服务器
ssh ubuntu@122.51.24.120

# 查看数据库密码
cat /opt/supawriter/.env | grep POSTGRES_PASSWORD
```

### 3. 安装依赖

确保已安装 `psycopg2` 库：

```bash
# 使用 uv（推荐）
uv pip install psycopg2-binary

# 或使用 pip
pip install psycopg2-binary
```

## 🚀 使用方法

### 方法一：命令行参数（推荐）

```bash
# 基本用法 - 迁移所有用户数据
python deployment/migrate/migrate_to_pgsql.py \
  --host 122.51.24.120 \
  --port 5432 \
  --user supawriter \
  --password YOUR_PASSWORD \
  --database supawriter

# 仅迁移指定用户
python deployment/migrate/migrate_to_pgsql.py \
  --host 122.51.24.120 \
  --password YOUR_PASSWORD \
  --username 104698863581745990403

# 测试数据库连接
python deployment/migrate/migrate_to_pgsql.py \
  --host 122.51.24.120 \
  --password YOUR_PASSWORD \
  --test
```

### 方法二：环境变量

创建 `.env.migration` 文件：

```bash
export POSTGRES_HOST=122.51.24.120
export POSTGRES_PORT=5432
export POSTGRES_USER=supawriter
export POSTGRES_PASSWORD=YOUR_PASSWORD
export POSTGRES_DB=supawriter
```

然后运行：

```bash
# 加载环境变量
source .env.migration

# 运行迁移
python deployment/migrate/migrate_to_pgsql.py

# 或使用 uv
uv run python deployment/migrate/migrate_to_pgsql.py
```

## 📊 迁移的数据类型

脚本会自动迁移以下数据：

### 1. 文章数据 (articles)
- 来源: `data/history/{username}_history.json`
- 包含字段:
  - 文章主题、内容、摘要
  - 模型信息（类型、名称）
  - 生成参数（写作类型、爬虫数量、自定义风格）
  - 图片设置（任务ID、相似度阈值、最大数量）
  - 标签、时间戳等

### 2. 聊天历史 (chat_sessions)
- 来源: `data/chat_history/{username}/*.json`
- 包含字段:
  - 会话标题
  - 消息列表
  - 创建时间、更新时间

### 3. 用户配置 (user_configs)
- 来源: `data/config/{username}_config.json`
- 包含字段:
  - 全局模型设置
  - 嵌入模型设置
  - 其他个性化配置

## 📝 命令行参数说明

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--host` | PostgreSQL服务器地址 | 122.51.24.120 | `--host 127.0.0.1` |
| `--port` | PostgreSQL端口 | 5432 | `--port 5432` |
| `--user` | 数据库用户名 | supawriter | `--user postgres` |
| `--password` | 数据库密码 | (必需) | `--password mypass` |
| `--database` | 数据库名 | supawriter | `--database mydb` |
| `--username` | 仅迁移指定用户 | 所有用户 | `--username user123` |
| `--test` | 仅测试连接 | False | `--test` |

## 🔍 运行示例

### 示例 1: 测试连接

```bash
python deployment/migrate/migrate_to_pgsql.py \
  --host 122.51.24.120 \
  --password ^1234qwerasdf$ \
  --test
```

预期输出：
```
2025-11-11 14:00:00 - INFO - 成功连接到PostgreSQL数据库 122.51.24.120:5432/supawriter
2025-11-11 14:00:00 - INFO - PostgreSQL版本: PostgreSQL 16.x on ...
2025-11-11 14:00:00 - INFO - 数据库连接测试成功！
```

### 示例 2: 迁移所有用户

```bash
python deployment/migrate/migrate_to_pgsql.py \
  --host 122.51.24.120 \
  --password ^1234qwerasdf$
```

预期输出：
```
2025-11-11 14:00:00 - INFO - 找到 3 个用户需要迁移: user1, user2, user3
============================================================
开始迁移用户: user1
============================================================
2025-11-11 14:00:01 - INFO - 用户 user1 迁移了 15/15 篇文章
2025-11-11 14:00:02 - INFO - 用户 user1 迁移了 8/8 个聊天会话
2025-11-11 14:00:02 - INFO - 用户 user1 配置迁移成功
...
============================================================
数据迁移完成！
============================================================
总计迁移:
  - 用户数: 3
  - 文章数: 45
  - 聊天会话数: 20
  - 用户配置数: 3
```

### 示例 3: 仅迁移指定用户

```bash
python deployment/migrate/migrate_to_pgsql.py \
  --host 122.51.24.120 \
  --password ^1234qwerasdf$ \
  --username 104698863581745990403
```

## 🔒 防止重复数据

为了防止重复迁移导致数据重复，需要为数据库表添加唯一约束。

### 方法1: 新建数据库（自动应用）

如果你是**新建的数据库**，约束已包含在 `01-init.sql` 中，会自动创建。

### 方法2: 现有数据库（手动应用）

如果数据库**已经在运行**，需要手动应用约束：

```bash
cd deployment/migrate
./apply_constraints.sh
```

脚本会：
1. ✅ 检查是否存在重复数据
2. ✅ 应用唯一约束到 articles 和 chat_sessions 表
3. ✅ 验证约束是否成功添加

**添加约束后的效果**：
- 重复迁移相同的文章或聊天会话会被自动忽略
- 迁移脚本中的 `ON CONFLICT DO NOTHING` 会正常工作
- 不会产生重复数据

### 方法3: 手动在pgAdmin执行

```sql
-- 为articles表添加唯一约束
ALTER TABLE articles 
    DROP CONSTRAINT IF EXISTS articles_unique_constraint;
ALTER TABLE articles 
    ADD CONSTRAINT articles_unique_constraint 
    UNIQUE (username, topic, created_at);

-- 为chat_sessions表添加唯一约束
ALTER TABLE chat_sessions 
    DROP CONSTRAINT IF EXISTS chat_sessions_unique_constraint;
ALTER TABLE chat_sessions 
    ADD CONSTRAINT chat_sessions_unique_constraint 
    UNIQUE (username, created_at);
```

## ⚠️ 注意事项

### 1. 数据安全
- **备份数据**: 迁移前建议备份本地数据和数据库
- **测试先行**: 先使用 `--test` 参数测试连接
- **逐步迁移**: 建议先迁移单个用户测试，确认无误后再迁移所有用户

### 2. 数据冲突处理

**添加唯一约束后**（推荐）：
- ✅ **文章**: 基于 `(username, topic, created_at)` 去重，相同数据会被忽略
- ✅ **聊天会话**: 基于 `(username, created_at)` 去重，相同数据会被忽略  
- ✅ **用户配置**: 基于 `username` 去重，会更新为最新配置

**未添加唯一约束**（不推荐）：
- ⚠️ 重复迁移会导致文章和聊天会话重复插入
- 建议尽快运行 `./apply_constraints.sh` 添加约束

### 3. 网络连接
- 确保本地能访问服务器的5432端口
- 检查服务器防火墙设置：
  ```bash
  # 在服务器上检查
  sudo ufw status | grep 5432
  
  # 如果未开放，需要开放端口
  sudo ufw allow 5432/tcp comment "PostgreSQL"
  ```

### 4. 密码包含特殊字符
如果密码包含特殊字符（如 `$`、`&`、`!` 等），建议：

**方法1**: 使用单引号包裹
```bash
python deployment/migrate/migrate_to_pgsql.py \
  --password '^1234qwerasdf$'
```

**方法2**: 使用环境变量
```bash
export POSTGRES_PASSWORD='^1234qwerasdf$'
python deployment/migrate/migrate_to_pgsql.py
```

**方法3**: 使用转义字符
```bash
python deployment/migrate/migrate_to_pgsql.py \
  --password \^1234qwerasdf\$
```

## 🔧 故障排除

### 问题 1: 连接被拒绝

**错误信息**:
```
连接数据库失败: could not connect to server: Connection refused
```

**解决方案**:
1. 检查服务器IP和端口是否正确
2. 确认服务器PostgreSQL服务是否运行：
   ```bash
   ssh ubuntu@122.51.24.120
   cd /opt/supawriter
   sudo ./manage.sh status
   ```
3. 检查防火墙设置

### 问题 2: 认证失败

**错误信息**:
```
连接数据库失败: FATAL: password authentication failed
```

**解决方案**:
1. 确认密码是否正确
2. 检查用户名是否正确
3. 在服务器上查看正确的密码：
   ```bash
   cat /opt/supawriter/.env | grep POSTGRES_PASSWORD
   ```

### 问题 3: 数据库不存在

**错误信息**:
```
连接数据库失败: FATAL: database "supawriter" does not exist
```

**解决方案**:
1. 确认数据库名是否正确
2. 在服务器上检查数据库：
   ```bash
   sudo docker-compose exec postgres psql -U supawriter -l
   ```

### 问题 4: 缺少依赖

**错误信息**:
```
ModuleNotFoundError: No module named 'psycopg2'
```

**解决方案**:
```bash
# 使用 uv
uv pip install psycopg2-binary

# 或使用 pip
pip install psycopg2-binary
```

## 📈 验证迁移结果

迁移完成后，可以在服务器上验证数据：

```bash
# 登录服务器
ssh ubuntu@122.51.24.120

# 连接数据库
sudo docker-compose exec postgres psql -U supawriter -d supawriter

# 查看文章数量
SELECT username, COUNT(*) as article_count 
FROM articles 
GROUP BY username;

# 查看聊天会话数量
SELECT username, COUNT(*) as session_count 
FROM chat_sessions 
GROUP BY username;

# 查看用户配置
SELECT username, created_at, updated_at 
FROM user_configs;

# 退出psql
\q
```

## 🔄 定期同步

如果需要定期将本地数据同步到服务器，可以创建定时任务：

```bash
# 创建同步脚本
cat > sync_to_server.sh << 'EOF'
#!/bin/bash
source .env.migration
python deployment/migrate/migrate_to_pgsql.py
EOF

chmod +x sync_to_server.sh

# 添加到 crontab（每天凌晨3点同步）
crontab -e
# 添加以下行：
# 0 3 * * * /path/to/supawriter/sync_to_server.sh >> /path/to/supawriter/logs/sync.log 2>&1
```

## 📞 技术支持

如遇到问题，请：
1. 检查日志输出的错误信息
2. 参考"故障排除"部分
3. 查看数据库连接配置
4. 确认网络连通性

---

**🎉 祝你数据迁移顺利！**
