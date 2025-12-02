# 🚀 SupaWriter 数据库快速参考

## 一句话部署

```bash
# 全新部署（最快）
cd deployment && ./quick_setup.sh

# 升级现有数据库
python scripts/migrate_database.py

# 测试系统
python scripts/test_auth_system.py
```

---

## 📁 重要文件速查

| 文件 | 用途 | 何时使用 |
|------|------|---------|
| `deployment/quick_setup.sh` | 一键部署脚本 | ⭐ 首选 |
| `deployment/postgres/init/00-init-complete.sql` | 完整SQL | Docker新部署 |
| `deployment/migrate/001_create_auth_tables.sql` | 认证表SQL | 手动升级 |
| `deployment/MIGRATION_GUIDE.md` | 详细指南 | 遇到问题时 |
| `scripts/migrate_database.py` | Python迁移 | 升级数据库 |
| `scripts/create_user.py` | 创建用户 | 添加用户 |
| `scripts/test_auth_system.py` | 测试脚本 | 验证部署 |

---

## 🎯 三种部署方式

### 方式1：Docker全新部署（推荐）⭐

```bash
cd deployment
docker-compose up -d postgres
sleep 10
docker exec supawriter_postgres psql -U supawriter -d supawriter -c "\dt"
```

**自动完成：**
- ✅ 创建所有表（5个）
- ✅ 创建索引和触发器
- ✅ 创建管理员账号（admin/admin123）

---

### 方式2：升级现有数据库

```bash
# 备份
pg_dump -U supawriter -d supawriter > backup.sql

# 升级
python scripts/migrate_database.py

# 测试
python scripts/test_auth_system.py
```

**会添加：**
- ✅ users表
- ✅ oauth_accounts表
- ✅ 相关索引

---

### 方式3：一键脚本（全能）

```bash
cd deployment
chmod +x quick_setup.sh
./quick_setup.sh

# 选择：
# 1) 全新部署（Docker）
# 2) 升级现有数据库
# 3) 仅迁移历史数据
```

---

## 🔧 常用命令

### Docker操作

```bash
# 启动
docker-compose -f deployment/docker-compose.yml up -d postgres

# 停止
docker-compose -f deployment/docker-compose.yml down

# 查看日志
docker-compose -f deployment/docker-compose.yml logs -f postgres

# 进入数据库
docker exec -it supawriter_postgres psql -U supawriter -d supawriter

# 重启
docker-compose -f deployment/docker-compose.yml restart postgres
```

### 数据库操作

```bash
# 连接数据库
psql -h localhost -U supawriter -d supawriter

# 查看表
\dt

# 查看表结构
\d users

# 查看用户
SELECT * FROM users;

# 退出
\q
```

### Python操作

```bash
# 安装依赖
pip install psycopg2-binary

# 执行迁移
python scripts/migrate_database.py

# 创建用户
python scripts/create_user.py

# 测试系统
python scripts/test_auth_system.py

# 启动应用
streamlit run web.py
```

---

## 🔐 默认账号

```
用户名: admin
密码: admin123
邮箱: admin@supawriter.com
```

⚠️ **首次登录后立即修改密码！**

---

## 📊 数据库表结构

```
users              ← 用户表
├── id
├── username
├── email
├── password_hash
├── display_name
├── avatar_url
├── motto
└── ...

oauth_accounts     ← OAuth绑定
├── id
├── user_id  ──────┘
├── provider
├── provider_user_id
└── ...

articles           ← 文章
├── id
├── username
├── topic
└── ...

chat_sessions      ← 聊天
├── id
├── username
└── ...

user_configs       ← 配置
├── id
├── username
└── ...
```

---

## 🆘 故障排查

### 问题：Docker容器无法启动

```bash
# 检查端口
lsof -i :5432

# 查看日志
docker-compose logs postgres

# 重新启动
docker-compose down && docker-compose up -d postgres
```

### 问题：连接数据库失败

```bash
# 测试连接
pg_isready -h localhost -p 5432 -U supawriter

# 检查配置
cat deployment/.env

# 检查容器状态
docker ps | grep postgres
```

### 问题：表已存在

```bash
# 查看现有表
psql -U supawriter -d supawriter -c "\dt"

# 删除旧表（谨慎！）
psql -U supawriter -d supawriter -c "DROP TABLE IF EXISTS oauth_accounts CASCADE;"
psql -U supawriter -d supawriter -c "DROP TABLE IF EXISTS users CASCADE;"
```

### 问题：迁移失败

```bash
# 查看详细错误
python scripts/migrate_database.py 2>&1 | tee error.log

# 手动执行SQL
psql -U supawriter -d supawriter -f deployment/migrate/001_create_auth_tables.sql
```

---

## ✅ 部署后检查

```bash
# 1. 检查表
psql -U supawriter -d supawriter -c "\dt"
# 应该有5个表

# 2. 检查管理员
psql -U supawriter -d supawriter -c "SELECT * FROM users WHERE username='admin';"
# 应该有1条记录

# 3. 运行测试
python scripts/test_auth_system.py
# 应该全部通过

# 4. 登录测试
streamlit run web.py
# 访问 http://localhost:8501
# 使用 admin/admin123 登录
```

---

## 📞 获取帮助

1. 查看详细文档：`deployment/MIGRATION_GUIDE.md`
2. 查看整合说明：`deployment/CLEANUP_SUMMARY.md`
3. 运行测试脚本：`python scripts/test_auth_system.py`
4. 联系技术支持：952718180@qq.com

---

## 🔖 快捷链接

- [详细迁移指南](MIGRATION_GUIDE.md)
- [整合总结](CLEANUP_SUMMARY.md)
- [认证系统文档](../AUTHENTICATION_V2_GUIDE.md)
- [快速开始](../QUICKSTART_AUTH_V2.md)

---

**最后更新**: 2025-01-17  
**版本**: V2.1
