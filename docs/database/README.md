# 数据库文档

## 📚 文档索引

### 核心文档

1. **[数据库架构文档](DATABASE_SCHEMA.md)** 📊
   - 完整的表结构说明
   - 字段类型和约束
   - 索引和视图
   - 函数和触发器

2. **[数据库初始化指南](DATABASE_INIT_GUIDE.md)** 🚀
   - 快速开始
   - 重建数据库
   - 验证和测试
   - 故障排除

### SQL 文件

- **完整初始化脚本**: `../../deployment/postgres/init/complete-init.sql`
  - 一键创建所有表、索引、视图、函数
  - 包含默认数据和注释
  - 可用于从零重建数据库
  - 整合了所有历史迁移内容

## 🎯 快速开始

### 初始化新数据库

```bash
# 方法1: 使用 psql
psql -U postgres -d supawriter -f deployment/postgres/init/complete-init.sql

# 方法2: 使用 Python
uv run python scripts/init_database.py
```

### 验证数据库

```sql
-- 检查表
\dt

-- 检查默认管理员
SELECT username, email FROM users WHERE username = 'admin';
```

## 📋 数据库概览

### 表分类

**认证系统** (2 tables)
- `users` - 用户表
- `oauth_accounts` - OAuth绑定表

**文章管理** (1 table)
- `articles` - 文章表

**聊天系统** (2 tables)
- `chat_sessions` - 聊天会话表
- `chat_messages` - 聊天消息表

**用户配置** (6 tables)
- `user_configs` - 用户配置表（旧版）
- `user_api_keys` - API密钥表
- `user_model_configs` - 模型配置表
- `user_preferences` - 用户偏好表
- `llm_providers` - LLM提供商表
- `user_service_configs` - 服务配置表

**系统配置** (1 table)
- `system_settings` - 系统设置表

### 视图

- `user_profile_view` - 用户完整信息视图
- `article_stats` - 文章统计视图

### 函数

- `update_updated_at_column()` - 自动更新时间戳
- `search_articles_fulltext()` - 全文搜索

## 🔐 默认账号

- **用户名**: admin
- **密码**: admin123
- **邮箱**: admin@supawriter.com

⚠️ **生产环境必须立即修改默认密码！**

## 📈 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-01-15 | 初始版本 |
| 2.0 | 2026-02-02 | 完整重构，统一架构 |

## 🔗 相关链接

- [部署指南](../deployment/frontend-backend-deployment.md)
- [架构指南](../../ARCHITECTURE_GUIDE.md)
- [API 文档](../api/README.md)

---

**维护者**: SupaWriter Team  
**最后更新**: 2026-02-02
