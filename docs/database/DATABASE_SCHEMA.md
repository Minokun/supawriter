# SupaWriter 数据库架构文档

## 📋 概览

SupaWriter 使用 PostgreSQL 数据库，包含认证系统、文章管理、聊天系统、用户配置等模块。

**版本**: 2.0  
**最后更新**: 2026-02-02

---

## 🗂️ 数据库表结构

### 一、认证系统 (Authentication)

#### 1. users - 用户表
存储系统用户的基本信息。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | SERIAL | 用户ID | PRIMARY KEY |
| username | VARCHAR(100) | 用户名 | UNIQUE, NOT NULL |
| email | VARCHAR(255) | 邮箱 | UNIQUE |
| password_hash | VARCHAR(255) | 密码哈希 | - |
| display_name | VARCHAR(100) | 显示名称 | - |
| avatar_url | TEXT | 头像URL | - |
| motto | VARCHAR(200) | 座右铭 | DEFAULT '创作改变世界' |
| is_active | BOOLEAN | 是否激活 | DEFAULT TRUE |
| is_superuser | BOOLEAN | 是否超级管理员 | DEFAULT FALSE |
| last_login | TIMESTAMPTZ | 最后登录时间 | - |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

**索引**:
- `idx_users_email` - 邮箱索引
- `idx_users_username` - 用户名索引
- `idx_users_created_at` - 创建时间索引

#### 2. oauth_accounts - OAuth绑定表
存储用户与第三方OAuth账号的绑定关系。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | SERIAL | 绑定ID | PRIMARY KEY |
| user_id | INTEGER | 用户ID | FK → users.id, NOT NULL |
| provider | VARCHAR(50) | OAuth提供商 | NOT NULL |
| provider_user_id | VARCHAR(255) | 提供商用户ID | NOT NULL |
| access_token | TEXT | 访问令牌 | - |
| refresh_token | TEXT | 刷新令牌 | - |
| token_expires_at | TIMESTAMPTZ | 令牌过期时间 | - |
| extra_data | JSONB | 额外数据 | - |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

**约束**:
- UNIQUE(provider, provider_user_id) - 同一OAuth账号只能绑定一个用户

**索引**:
- `idx_oauth_user_id` - 用户ID索引
- `idx_oauth_provider` - 提供商复合索引

---

### 二、文章管理 (Articles)

#### 3. articles - 文章表
存储用户创作的文章内容。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 文章ID | PRIMARY KEY |
| username | VARCHAR(100) | 用户名 | NOT NULL |
| topic | VARCHAR(500) | 文章主题 | NOT NULL |
| article_content | TEXT | 文章内容 | NOT NULL |
| summary | TEXT | 摘要 | - |
| tags | TEXT[] | 标签数组 | - |
| metadata | JSONB | 元数据 | DEFAULT '{}' |
| model_type | VARCHAR(50) | 模型类型 | - |
| model_name | VARCHAR(100) | 模型名称 | - |
| write_type | VARCHAR(50) | 写作类型 | - |
| spider_num | INTEGER | 爬虫数量 | - |
| custom_style | TEXT | 自定义风格 | - |
| is_transformed | BOOLEAN | 是否已转换 | DEFAULT FALSE |
| original_article_id | UUID | 原文章ID | FK → articles.id |
| image_task_id | VARCHAR(100) | 图片任务ID | - |
| image_enabled | BOOLEAN | 是否启用图片 | DEFAULT FALSE |
| image_similarity_threshold | DECIMAL(3,2) | 图片相似度阈值 | - |
| image_max_count | INTEGER | 最大图片数量 | - |
| article_topic | TEXT | 文章话题 | - |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

**索引**:
- `idx_articles_username` - 用户名索引
- `idx_articles_created_at` - 创建时间索引
- `idx_articles_tags` - 标签GIN索引
- `idx_articles_metadata` - 元数据GIN索引
- `idx_articles_topic` - 主题索引
- `idx_articles_fulltext_*` - 全文搜索索引

---

### 三、聊天系统 (Chat)

#### 4. chat_sessions - 聊天会话表
存储用户与AI的对话会话。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 会话ID | PRIMARY KEY |
| user_id | INTEGER | 用户ID | FK → users.id, NOT NULL |
| username | VARCHAR(100) | 用户名（兼容） | - |
| title | VARCHAR(500) | 会话标题 | - |
| model | VARCHAR(100) | 使用的模型 | - |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

**索引**:
- `idx_chat_sessions_user_id` - 用户ID索引
- `idx_chat_sessions_created_at` - 创建时间索引
- `idx_chat_sessions_user_created` - 用户+时间复合索引

#### 5. chat_messages - 聊天消息表
存储用户与AI的单条对话消息。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 消息ID | PRIMARY KEY |
| session_id | UUID | 会话ID | FK → chat_sessions.id, NOT NULL |
| user_id | INTEGER | 用户ID | FK → users.id, NOT NULL |
| role | VARCHAR(20) | 角色 | NOT NULL |
| content | TEXT | 消息内容 | NOT NULL |
| thinking | TEXT | AI思考过程 | - |
| model | VARCHAR(100) | 使用的模型 | - |
| timestamp | TIMESTAMPTZ | 时间戳 | DEFAULT NOW() |

**角色类型**:
- `user` - 用户消息
- `assistant` - AI助手消息
- `system` - 系统消息

**索引**:
- `idx_chat_messages_session_id` - 会话ID索引
- `idx_chat_messages_user_id` - 用户ID索引
- `idx_chat_messages_timestamp` - 时间戳索引
- `idx_chat_messages_session_timestamp` - 会话+时间复合索引

---

### 四、用户配置 (User Settings)

#### 6. user_configs - 用户配置表（旧版）
存储用户的个性化配置（JSONB格式）。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 配置ID | PRIMARY KEY |
| username | VARCHAR(100) | 用户名 | UNIQUE, NOT NULL |
| config | JSONB | 配置JSON | DEFAULT '{}' |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

#### 7. user_api_keys - API密钥表
存储用户的API密钥（加密存储）。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | SERIAL | 密钥ID | PRIMARY KEY |
| user_id | INTEGER | 用户ID | FK → users.id, NOT NULL |
| provider | VARCHAR(50) | 提供商 | NOT NULL |
| api_key_encrypted | TEXT | 加密的API密钥 | NOT NULL |
| key_preview | VARCHAR(20) | 密钥预览 | - |
| is_active | BOOLEAN | 是否激活 | DEFAULT TRUE |
| last_used_at | TIMESTAMPTZ | 最后使用时间 | - |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

**约束**:
- UNIQUE(user_id, provider) - 每个用户每个提供商只能有一个密钥

#### 8. user_model_configs - 模型配置表
存储用户的AI模型配置。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| user_id | INTEGER | 用户ID | PRIMARY KEY, FK → users.id |
| chat_model | VARCHAR(100) | 聊天模型 | DEFAULT 'deepseek/deepseek-chat' |
| writer_model | VARCHAR(100) | 写作模型 | DEFAULT 'deepseek/deepseek-chat' |
| embedding_model | VARCHAR(100) | 嵌入模型 | DEFAULT 'text-embedding-3-small' |
| image_model | VARCHAR(100) | 图像模型 | DEFAULT 'dall-e-3' |
| default_temperature | DECIMAL(3,2) | 默认温度 | DEFAULT 0.7 |
| default_max_tokens | INTEGER | 默认最大令牌数 | DEFAULT 2000 |
| default_top_p | DECIMAL(3,2) | 默认Top-P | DEFAULT 1.0 |
| enable_streaming | BOOLEAN | 启用流式输出 | DEFAULT TRUE |
| enable_thinking_process | BOOLEAN | 启用思考过程 | DEFAULT TRUE |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

#### 9. user_preferences - 用户偏好表
存储用户的界面和行为偏好。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| user_id | INTEGER | 用户ID | PRIMARY KEY, FK → users.id |
| editor_font_size | INTEGER | 编辑器字体大小 | DEFAULT 14 |
| editor_theme | VARCHAR(20) | 编辑器主题 | DEFAULT 'vs-light' |
| auto_save_interval | INTEGER | 自动保存间隔(秒) | DEFAULT 30 |
| default_article_style | VARCHAR(50) | 默认文章风格 | DEFAULT 'professional' |
| default_article_length | VARCHAR(20) | 默认文章长度 | DEFAULT 'medium' |
| default_language | VARCHAR(10) | 默认语言 | DEFAULT 'zh-CN' |
| sidebar_collapsed | BOOLEAN | 侧边栏折叠 | DEFAULT FALSE |
| theme_mode | VARCHAR(10) | 主题模式 | DEFAULT 'light' |
| email_notifications | BOOLEAN | 邮件通知 | DEFAULT TRUE |
| task_complete_notification | BOOLEAN | 任务完成通知 | DEFAULT TRUE |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

#### 10. llm_providers - LLM提供商表
存储用户配置的LLM提供商。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | SERIAL | 提供商ID | PRIMARY KEY |
| user_id | INTEGER | 用户ID | FK → users.id, NOT NULL |
| provider_id | VARCHAR(50) | 提供商标识 | NOT NULL |
| provider_name | VARCHAR(100) | 提供商名称 | NOT NULL |
| base_url | TEXT | API基础URL | NOT NULL |
| api_key_encrypted | TEXT | 加密的API密钥 | - |
| models | JSONB | 支持的模型列表 | DEFAULT '[]' |
| enabled | BOOLEAN | 是否启用 | DEFAULT TRUE |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

**约束**:
- UNIQUE(user_id, provider_id)

#### 11. user_service_configs - 服务配置表
存储用户的其他服务配置（七牛云、SERPER等）。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | SERIAL | 配置ID | PRIMARY KEY |
| user_id | INTEGER | 用户ID | UNIQUE, FK → users.id, NOT NULL |
| qiniu_domain | VARCHAR(255) | 七牛云域名 | - |
| qiniu_folder | VARCHAR(255) | 七牛云文件夹 | - |
| qiniu_access_key_encrypted | TEXT | 七牛云AK（加密） | - |
| qiniu_secret_key_encrypted | TEXT | 七牛云SK（加密） | - |
| qiniu_region | VARCHAR(10) | 七牛云区域 | - |
| serper_api_key_encrypted | TEXT | SERPER密钥（加密） | - |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

---

### 五、系统配置 (System Settings)

#### 12. system_settings - 系统设置表
存储全局系统配置。

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | SERIAL | 设置ID | PRIMARY KEY |
| setting_key | VARCHAR(100) | 配置键 | UNIQUE, NOT NULL |
| setting_value | TEXT | 配置值 | NOT NULL |
| setting_type | VARCHAR(20) | 配置类型 | DEFAULT 'string' |
| description | TEXT | 描述 | - |
| is_encrypted | BOOLEAN | 是否加密 | DEFAULT FALSE |
| created_at | TIMESTAMPTZ | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | 更新时间 | DEFAULT NOW() |

**配置类型**:
- `string` - 字符串
- `json` - JSON对象
- `boolean` - 布尔值
- `number` - 数字

---

## 📊 视图 (Views)

### user_profile_view - 用户完整信息视图
聚合用户基本信息和OAuth绑定信息。

```sql
SELECT 
    u.id, u.username, u.email, u.display_name, 
    u.avatar_url, u.motto, u.is_active, 
    u.last_login, u.created_at,
    oauth_accounts (JSON数组)
FROM users u
LEFT JOIN oauth_accounts oa ON u.id = oa.user_id
```

### article_stats - 文章统计视图
按用户统计文章数据。

```sql
SELECT 
    username,
    total_articles,              -- 总文章数
    articles_last_7_days,        -- 最近7天文章数
    articles_last_30_days,       -- 最近30天文章数
    avg_content_length,          -- 平均内容长度
    last_article_date            -- 最后文章日期
FROM articles
GROUP BY username
```

---

## 🔧 函数 (Functions)

### update_updated_at_column()
触发器函数，自动更新 `updated_at` 字段。

**用途**: 在 UPDATE 操作时自动设置 `updated_at = CURRENT_TIMESTAMP`

### search_articles_fulltext()
全文搜索函数。

**参数**:
- `search_query` TEXT - 搜索查询
- `user_id` TEXT - 用户ID（可选）
- `limit_count` INTEGER - 限制数量（默认20）
- `offset_count` INTEGER - 偏移量（默认0）

**返回**: 匹配的文章列表（按相关性排序）

---

## 🔐 安全性

### 加密字段
以下字段使用 Fernet 加密存储：
- `user_api_keys.api_key_encrypted`
- `llm_providers.api_key_encrypted`
- `user_service_configs.*_encrypted`

### 默认账号
- **用户名**: admin
- **密码**: admin123（SHA256哈希）
- **邮箱**: admin@supawriter.com

⚠️ **生产环境必须立即修改默认密码！**

---

## 🚀 初始化

### 完整初始化
```bash
psql -U postgres -d supawriter -f deployment/postgres/init/complete-init.sql
```

### 验证初始化
```sql
-- 检查表数量
SELECT count(*) FROM information_schema.tables 
WHERE table_schema = 'public';

-- 检查默认管理员
SELECT username, email, is_superuser FROM users WHERE username = 'admin';
```

---

## 📈 性能优化

### 索引策略
- **单列索引**: 用于频繁查询的列（username, email, created_at等）
- **复合索引**: 用于多条件查询（user_id + created_at等）
- **GIN索引**: 用于JSONB、数组、全文搜索

### 分析表
定期运行 `ANALYZE` 更新统计信息：
```sql
ANALYZE users;
ANALYZE articles;
ANALYZE chat_sessions;
ANALYZE chat_messages;
```

---

## 🔄 迁移历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-01-15 | 初始版本 |
| 1.1 | 2026-01-30 | 添加用户设置表 |
| 1.2 | 2026-01-31 | 添加聊天消息表 |
| 2.0 | 2026-02-02 | 完整重构，统一架构 |

---

## 📚 相关文档

- [API 文档](../api/README.md)
- [部署指南](../deployment/frontend-backend-deployment.md)
- [架构指南](../../ARCHITECTURE_GUIDE.md)

---

**维护者**: SupaWriter Team  
**最后更新**: 2026-02-02
