# SupaWriter PostgreSQL 部署文档

## 📋 部署前准备

### 1. 服务器要求
- **操作系统**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **配置要求**: 最低 2核2GB，推荐 4核4GB
- **网络要求**: 公网IP，开放端口 22(SSH)、5432(PostgreSQL)、8080(pgAdmin)
- **权限要求**: sudo 权限

### 2. 本地环境要求
- **SSH客户端**: 支持 ssh、scp 命令
- **网络连接**: 能够访问目标服务器

### 3. 配置服务器信息

在开始部署前，需要配置目标服务器信息：

#### 方法一：修改脚本默认配置
编辑 `scripts/quick-deploy.sh` 和 `scripts/setup-ssh-key.sh`：
```bash
# 修改默认服务器配置
SERVER_IP="YOUR_SERVER_IP"        # 替换为你的服务器IP
SERVER_USER="YOUR_USERNAME"       # 替换为你的用户名（如 ubuntu、root）
```

#### 方法二：使用命令行参数
```bash
./quick-deploy.sh --server-ip YOUR_SERVER_IP --server-user YOUR_USERNAME
./setup-ssh-key.sh --server-ip YOUR_SERVER_IP --server-user YOUR_USERNAME
```

### 4. 配置数据库密码

编辑 `.env` 文件，设置数据库密码：
```bash
# 修改以下配置
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD      # PostgreSQL 密码
PGADMIN_PASSWORD=YOUR_ADMIN_PASSWORD        # pgAdmin 密码
DATABASE_URL=postgresql://supawriter:YOUR_SECURE_PASSWORD@postgres:5432/supawriter
```

**⚠️ 安全提醒**: 
- 使用强密码（建议包含大小写字母、数字、特殊字符）
- 不要在代码仓库中提交真实密码
- 生产环境建议定期更换密码

## 📁 目录结构

```
deployment/
├── README.md                    # 📖 部署文档
├── docker-compose.yml           # 🐳 Docker 编排配置
├── .env                         # ⚙️ 环境变量配置（包含密码）
├── .env.example                 # 📝 环境变量配置示例
├── servers.conf.example         # 🖥️ 服务器配置示例
├── migrate/                     # 📤 数据迁移工具
│   ├── README.md               # 📘 迁移文档
│   ├── migrate_to_pgsql.py     # 🔄 迁移脚本
│   ├── quick_migrate.sh        # ⚡ 快速迁移脚本
│   └── .env.migration.example  # 📝 迁移配置示例
├── postgres/                    # 🗄️ PostgreSQL 配置
│   ├── config/
│   │   ├── postgresql.conf      # 📋 PostgreSQL 主配置
│   │   └── pg_hba.conf         # 🔐 访问控制配置
│   └── init/
│       └── 01-init.sql         # 🚀 数据库初始化脚本
└── scripts/                     # 📜 部署和管理脚本
    ├── deploy.sh               # 🔧 服务器端部署脚本
    ├── manage.sh               # 🛠️ 服务器端管理脚本
    ├── quick-deploy.sh         # ⚡ 本地快速部署脚本
    └── setup-ssh-key.sh        # 🔑 SSH密钥配置脚本
```

## 🚀 部署方式

### 方式一：快速部署（推荐）

#### 步骤 1: 配置部署信息
```bash
# 进入部署目录
cd deployment

# 1. 配置服务器信息（二选一）
# 方法A：修改脚本文件
vim scripts/quick-deploy.sh
# 找到并修改：
# SERVER_IP="YOUR_SERVER_IP"
# SERVER_USER="YOUR_USERNAME"

# 方法B：使用命令行参数（见步骤3）

# 2. 配置数据库密码
vim .env
# 修改以下行：
# POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD
# PGLADMIN_PASSWORD=YOUR_ADMIN_PASSWORD
# DATABASE_URL=postgresql://supawriter:YOUR_SECURE_PASSWORD@postgres:5432/supawriter
```

#### 步骤 2: 配置SSH密钥（推荐）
```bash
cd scripts

# 设置执行权限
chmod +x setup-ssh-key.sh

# 配置SSH密钥认证（避免多次输入密码）
./setup-ssh-key.sh

# 或指定服务器信息
./setup-ssh-key.sh --server-ip YOUR_SERVER_IP --server-user YOUR_USERNAME
```

#### 步骤 3: 执行部署
```bash
# 设置执行权限
chmod +x quick-deploy.sh

# 使用默认配置部署
./quick-deploy.sh

# 或指定服务器信息部署
./quick-deploy.sh --server-ip YOUR_SERVER_IP --server-user YOUR_USERNAME
```

#### 步骤 4: 验证部署
```bash
# 部署完成后，验证服务状态
ssh YOUR_USERNAME@YOUR_SERVER_IP
cd /opt/supawriter
sudo ./manage.sh status
```

### 方式二：手动部署

```bash
# 1. 配置部署信息（同方式一的步骤1）
cd deployment
vim .env  # 配置数据库密码

# 2. 上传文件到服务器
scp -r . YOUR_USERNAME@YOUR_SERVER_IP:/tmp/deployment/

# 3. 登录服务器执行部署
ssh YOUR_USERNAME@YOUR_SERVER_IP
cd /tmp/deployment/scripts
chmod +x deploy.sh manage.sh
sudo ./deploy.sh

# 4. 验证部署
cd /opt/supawriter
sudo ./manage.sh status
```

### 方式三：仅配置脚本（适用于多次部署）

如果需要在多台服务器上部署，建议创建配置文件：

```bash
# 1. 创建服务器配置文件
cat > servers.conf << EOF
# 生产服务器
PROD_SERVER_IP="PROD_SERVER_IP"
PROD_SERVER_USER="ubuntu"

# 测试服务器  
TEST_SERVER_IP="TEST_SERVER_IP"
TEST_SERVER_USER="ubuntu"

# 开发服务器
DEV_SERVER_IP="DEV_SERVER_IP" 
DEV_SERVER_USER="root"
EOF

# 2. 使用配置文件部署
source servers.conf
./quick-deploy.sh --server-ip $PROD_SERVER_IP --server-user $PROD_SERVER_USER
```

## 🛠️ 服务管理

部署完成后，可以使用管理脚本进行日常运维：

```bash
# 进入项目目录
cd /opt/supawriter

# 查看服务状态
sudo ./manage.sh status

# 启动/停止/重启服务
sudo ./manage.sh start
sudo ./manage.sh stop
sudo ./manage.sh restart

# 查看日志
sudo ./manage.sh logs              # 所有服务日志
sudo ./manage.sh logs postgres     # PostgreSQL 日志

# 备份数据库
sudo ./manage.sh backup

# 恢复数据库
sudo ./manage.sh restore backup_file.sql.gz

# 系统监控
sudo ./manage.sh monitor

# 重新加载配置
sudo ./manage.sh update-config
```

## 🔧 配置说明

### 环境变量 (.env)

```bash
# PostgreSQL 配置
POSTGRES_PASSWORD=^1234qwerasdf$    # 数据库密码
POSTGRES_HOST=postgres              # 主机名
POSTGRES_PORT=5432                  # 端口
POSTGRES_DB=supawriter             # 数据库名
POSTGRES_USER=supawriter           # 用户名

# pgAdmin 配置
PGADMIN_PASSWORD=^1234qwerasdf$    # pgAdmin 密码

# 应用配置
DATABASE_URL=postgresql://supawriter:^1234qwerasdf$@postgres:5432/supawriter
```

### PostgreSQL 配置 (postgresql.conf)

针对 4核4G 服务器优化：

```bash
# 内存配置
shared_buffers = 1GB               # 25% 内存
effective_cache_size = 3GB         # 75% 内存
work_mem = 64MB                    # 单查询内存

# 连接配置
max_connections = 200              # 最大连接数
listen_addresses = '*'             # 监听所有IP

# 性能优化
random_page_cost = 1.1             # SSD 优化
effective_io_concurrency = 200     # 并发IO
```

### 访问控制 (pg_hba.conf)

```bash
# 允许所有IP连接（需要密码验证）
host    all    all    0.0.0.0/0    md5

# 本地连接
local   all    all                 trust
host    all    all    127.0.0.1/32 md5
```

## 🌐 访问信息

### PostgreSQL 数据库

- **主机**: `YOUR_SERVER_IP`
- **端口**: `5432`
- **数据库**: `supawriter`
- **用户名**: `supawriter`
- **密码**: `在 .env 文件中配置的 POSTGRES_PASSWORD`

**连接字符串格式**:
```
postgresql://supawriter:YOUR_PASSWORD@YOUR_SERVER_IP:5432/supawriter
```

### pgAdmin 管理界面

- **访问地址**: `http://YOUR_SERVER_IP:8080`
- **邮箱**: `admin@supawriter.com`
- **密码**: `在 .env 文件中配置的 PGADMIN_PASSWORD`

**📝 获取实际访问信息**:
部署完成后，脚本会显示实际的访问地址和密码信息。你也可以通过以下命令查看：
```bash
# 查看配置信息
ssh YOUR_USERNAME@YOUR_SERVER_IP
cat /opt/supawriter/.env | grep PASSWORD
```

## 📊 性能指标

### 4核4G 服务器预期性能

```yaml
硬件配置:
  CPU: 4核
  内存: 4GB
  存储: SSD

性能指标:
  并发连接: 200-300
  QPS: 2000-3000
  支持用户: 500-1000人
  文章存储: 50-100万篇
  全文搜索: <1秒响应
  
资源使用:
  PostgreSQL: ~1.5GB 内存
  Redis: ~100MB 内存
  pgAdmin: ~50MB 内存
  系统预留: ~2GB 内存
```

## 🔐 安全配置

### 防火墙设置

```bash
# 开放必要端口
sudo ufw allow 22/tcp comment "SSH"
sudo ufw allow 5432/tcp comment "PostgreSQL"
sudo ufw allow 8080/tcp comment "pgAdmin"
sudo ufw enable
sudo ufw reload

# 查看防火墙状态
sudo ufw status

# 限制SSH访问（可选，提高安全性）
sudo ufw delete allow 22/tcp
sudo ufw allow from YOUR_LOCAL_IP to any port 22 comment "SSH from specific IP"
```

### SSL 配置（可选）

```bash
# 生成SSL证书
sudo openssl req -new -x509 -days 365 -nodes -text \
  -out /opt/supawriter/postgres/ssl/server.crt \
  -keyout /opt/supawriter/postgres/ssl/server.key

# 修改配置启用SSL
echo "ssl = on" >> /opt/supawriter/postgres/config/postgresql.conf
```

### 密码安全

```bash
# 修改密码
sudo vi /opt/supawriter/.env

# 重启服务应用新密码
sudo ./manage.sh restart
```

## 📈 监控和维护

### 日常监控

```bash
# 系统资源监控
sudo ./manage.sh monitor

# 数据库性能监控
sudo docker-compose exec postgres psql -U supawriter -d supawriter -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"
```

### 备份策略

```bash
# 自动备份（已配置 cron）
0 2 * * * /opt/supawriter/manage.sh backup

# 手动备份
sudo ./manage.sh backup

# 备份文件位置
ls -la /opt/supawriter/postgres/backups/
```

### 日志管理

```bash
# 查看实时日志
sudo ./manage.sh logs

# 清理旧日志
sudo docker-compose exec postgres find /var/lib/postgresql/data/log -name "*.log" -mtime +7 -delete
```

## 🚨 故障排除

### 常见问题

**1. 服务启动失败**
```bash
# 检查日志
sudo ./manage.sh logs postgres

# 检查权限
sudo chown -R 999:999 /opt/supawriter/postgres/data
```

**2. 连接被拒绝**
```bash
# 检查端口
sudo netstat -tlnp | grep 5432

# 检查防火墙
sudo ufw status
```

**3. 内存不足**
```bash
# 检查内存使用
free -h
sudo docker stats

# 调整配置
sudo vi /opt/supawriter/postgres/config/postgresql.conf
```

**4. 磁盘空间不足**
```bash
# 检查磁盘使用
df -h

# 清理备份文件
find /opt/supawriter/postgres/backups -name "*.gz" -mtime +30 -delete
```

### 紧急恢复

```bash
# 停止所有服务
sudo ./manage.sh stop

# 恢复最新备份
sudo ./manage.sh restore /opt/supawriter/postgres/backups/latest_backup.sql.gz

# 重启服务
sudo ./manage.sh start
```

## 📞 技术支持

### 有用的命令

```bash
# 查看数据库大小
sudo docker-compose exec postgres psql -U supawriter -d supawriter -c "
SELECT pg_size_pretty(pg_database_size('supawriter')) as db_size;
"

# 查看连接数
sudo docker-compose exec postgres psql -U supawriter -d supawriter -c "
SELECT count(*) as connections, state FROM pg_stat_activity GROUP BY state;
"

# 查看慢查询
sudo docker-compose exec postgres psql -U supawriter -d supawriter -c "
SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 5;
"
```

---

## ✅ 快速配置检查清单

### 部署前检查
- [ ] **服务器准备**: 确认服务器IP、用户名、sudo权限
- [ ] **网络连接**: 确认本地能SSH连接到服务器
- [ ] **端口开放**: 确认服务器开放了22、5432、8080端口
- [ ] **配置服务器信息**: 修改脚本中的 `SERVER_IP` 和 `SERVER_USER`
- [ ] **配置数据库密码**: 修改 `.env` 文件中的密码配置
- [ ] **SSH密钥配置**: 运行 `setup-ssh-key.sh`（推荐）

### 部署后检查
- [ ] **服务状态**: 运行 `sudo ./manage.sh status` 确认所有服务正常
- [ ] **数据库连接**: 测试 PostgreSQL 连接
- [ ] **pgAdmin访问**: 访问 `http://YOUR_SERVER_IP:8080`
- [ ] **防火墙配置**: 配置 ufw 防火墙规则
- [ ] **备份测试**: 运行 `sudo ./manage.sh backup` 测试备份
- [ ] **SSL配置**: 生产环境配置SSL证书（可选）
- [ ] **密码安全**: 确认密码强度，定期更换
- [ ] **监控设置**: 配置服务监控和告警

### 常见问题排查
```bash
# 1. 检查服务状态
sudo docker-compose ps

# 2. 查看服务日志
sudo docker-compose logs postgres
sudo docker-compose logs pgadmin

# 3. 测试数据库连接
sudo docker-compose exec postgres pg_isready -U supawriter -d supawriter

# 4. 检查端口监听
sudo netstat -tlnp | grep -E "(5432|8080)"

# 5. 查看防火墙状态
sudo ufw status verbose
```

## 🆘 故障排除快速指南

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| SSH连接失败 | IP/用户名错误、网络问题 | 检查服务器信息，测试网络连通性 |
| 文件上传失败 | 权限问题、磁盘空间不足 | 检查服务器权限和磁盘空间 |
| 服务启动失败 | 端口冲突、配置错误 | 检查端口占用，查看服务日志 |
| 数据库连接失败 | 密码错误、网络问题 | 检查密码配置，确认防火墙设置 |
| pgAdmin无法访问 | 端口未开放、服务未启动 | 检查防火墙，确认服务状态 |

## 📤 数据迁移

部署完成后，可以将本地 JSON 数据迁移到服务器的 PostgreSQL 数据库。

### 快速迁移

```bash
# 进入迁移目录
cd migrate

# 配置数据库连接
cp .env.migration.example .env.migration
vim .env.migration  # 设置 POSTGRES_PASSWORD

# 运行交互式迁移工具
./quick_migrate.sh
```

### 迁移的数据类型

- **文章数据** (articles): 用户创作的所有文章内容、配置和元数据
- **聊天历史** (chat_sessions): AI 对话会话记录
- **用户配置** (user_configs): 个性化设置和偏好

### 详细说明

完整的迁移文档请参考：[migrate/README.md](migrate/README.md)

包含：
- 详细的使用方法和命令行参数
- 数据迁移流程说明
- 故障排除指南
- 验证和同步方案

## 📞 获取帮助

- **查看日志**: `sudo ./manage.sh logs`
- **系统监控**: `sudo ./manage.sh monitor`
- **服务重启**: `sudo ./manage.sh restart`
- **备份数据**: `sudo ./manage.sh backup`

### 联系信息

- 项目地址: https://github.com/your-repo/supawriter
- 文档地址: https://docs.supawriter.com
- 问题反馈: https://github.com/your-repo/supawriter/issues

---

**🎉 部署完成！享受高性能的 PostgreSQL 数据库服务！**
