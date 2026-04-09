# 数据库架构更新日志

## 2026-02-03: Articles 表添加 user_id 字段

### 更新原因
前后端分离版本（Next.js + FastAPI）的后端 API 使用 `user_id` 字段来关联用户，但数据库表中只有 `username` 字段，导致文章创作后无法保存到数据库。

### 更新内容

#### 1. Articles 表结构变更

**添加字段**:
```sql
ALTER TABLE articles 
ADD COLUMN user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE;
```

**添加索引**:
```sql
CREATE INDEX idx_articles_user_id ON articles(user_id);
```

#### 2. 数据迁移

从现有的 `username` 字段迁移数据到 `user_id`:
```sql
UPDATE articles a
SET user_id = u.id
FROM users u
WHERE a.username = u.username;
```

**迁移结果**:
- ✅ 已更新 17 条记录
- ✅ 3 个不同用户的数据

#### 3. 更新的文件

**部署 SQL 脚本**:
- `deployment/postgres/init/complete-init.sql`
  - 在 articles 表定义中添加 `user_id` 字段
  - 添加 `idx_articles_user_id` 索引

**迁移脚本**:
- `scripts/add_user_id_to_articles.py` - 用于现有数据库的迁移

### 更新后的表结构

```sql
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- 新增
    username VARCHAR(100) NOT NULL,  -- 保留用于兼容
    topic VARCHAR(500) NOT NULL,
    article_content TEXT NOT NULL,
    summary TEXT,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    model_type VARCHAR(50),
    model_name VARCHAR(100),
    write_type VARCHAR(50),
    spider_num INTEGER,
    custom_style TEXT,
    is_transformed BOOLEAN DEFAULT FALSE,
    original_article_id UUID REFERENCES articles(id),
    image_task_id VARCHAR(100),
    image_enabled BOOLEAN DEFAULT FALSE,
    image_similarity_threshold DECIMAL(3,2),
    image_max_count INTEGER,
    article_topic TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_articles_user_id ON articles(user_id);        -- 新增
CREATE INDEX idx_articles_username ON articles(username);
CREATE INDEX idx_articles_created_at ON articles(created_at DESC);
-- ... 其他索引
```

### 影响范围

**前端 (Next.js)**:
- ✅ 无需修改，前端通过 API 调用，不直接访问数据库

**后端 (FastAPI)**:
- ✅ `backend/api/routes/articles.py` - 已使用 `user_id`
- ✅ `backend/api/routes/articles_enhanced.py` - 已使用 `user_id`

**Streamlit 版本**:
- ✅ 无影响，继续使用 `username` 字段
- ✅ `utils/history_utils.py` 已更新，同时保存到 `user_id` 和 `username`

### 向后兼容性

- ✅ 保留 `username` 字段，确保 Streamlit 版本继续工作
- ✅ 新增 `user_id` 字段，支持前后端分离版本
- ✅ 两个字段同时维护，确保数据一致性

### 验证步骤

1. **检查表结构**:
```bash
uv run python scripts/check_articles_table.py
```

2. **测试文章创建**:
```bash
# 访问前端
http://localhost:3000

# 登录并创作文章
# 检查数据库中是否有新记录
```

3. **验证数据**:
```sql
SELECT id, user_id, username, topic, created_at 
FROM articles 
ORDER BY created_at DESC 
LIMIT 5;
```

### 相关问题修复

同时修复了以下问题：
- ✅ 启用了 `articles_enhanced.router`，恢复文章生成 API
- ✅ 修复了 CORS 配置，确保前端可以正常调用后端 API
- ✅ 添加了 `chat_messages` 和 `user_api_keys` 表

---

**更新人**: Cascade AI  
**更新时间**: 2026-02-03  
**影响版本**: v2.0+
