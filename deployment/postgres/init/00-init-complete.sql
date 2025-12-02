-- SupaWriter 完整数据库初始化脚本
-- 包含认证系统和应用数据表
-- Docker容器启动时自动执行

-- =============================================================================
-- 第一部分：扩展和函数
-- =============================================================================

-- 创建PostgreSQL扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索

-- 创建更新时间触发器函数（全局共用）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =============================================================================
-- 第二部分：认证系统表（新增）
-- =============================================================================

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),  -- 邮箱登录的密码哈希，OAuth用户可为空
    display_name VARCHAR(100),   -- 显示名称
    avatar_url TEXT,             -- 头像URL
    motto VARCHAR(200) DEFAULT '创作改变世界',  -- 座右铭
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    
    -- 注意：至少要有密码或OAuth账号的约束在应用层验证
    -- PostgreSQL不允许在CHECK约束中使用子查询
);

-- 创建OAuth账号绑定表
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- google, wechat等
    provider_user_id VARCHAR(255) NOT NULL,  -- OAuth提供商的用户ID
    access_token TEXT,              -- 访问令牌
    refresh_token TEXT,             -- 刷新令牌
    token_expires_at TIMESTAMP,     -- 令牌过期时间
    extra_data JSONB,               -- 存储额外的用户信息（如昵称、头像等）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 同一个OAuth账号只能绑定到一个用户
    UNIQUE(provider, provider_user_id)
);

-- 认证系统索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_oauth_user_id ON oauth_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_provider ON oauth_accounts(provider, provider_user_id);

-- 认证系统触发器
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_oauth_accounts_updated_at ON oauth_accounts;
CREATE TRIGGER update_oauth_accounts_updated_at 
    BEFORE UPDATE ON oauth_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入默认管理员账号（密码为: admin123）
INSERT INTO users (username, email, password_hash, display_name, is_superuser)
VALUES ('admin', 'admin@supawriter.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', '管理员', TRUE)
ON CONFLICT (username) DO NOTHING;

-- 创建用户完整信息视图
CREATE OR REPLACE VIEW user_profile_view AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.display_name,
    u.avatar_url,
    u.motto,
    u.is_active,
    u.last_login,
    u.created_at,
    COALESCE(
        json_agg(
            json_build_object(
                'provider', oa.provider,
                'provider_user_id', oa.provider_user_id,
                'created_at', oa.created_at
            )
        ) FILTER (WHERE oa.id IS NOT NULL),
        '[]'
    ) as oauth_accounts
FROM users u
LEFT JOIN oauth_accounts oa ON u.id = oa.user_id
GROUP BY u.id, u.username, u.email, u.display_name, u.avatar_url, u.motto, u.is_active, u.last_login, u.created_at;

-- =============================================================================
-- 第三部分：应用数据表
-- =============================================================================

-- 创建文章表
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL,
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

-- 创建聊天会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL,
    title VARCHAR(500),
    messages JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建用户配置表
CREATE TABLE IF NOT EXISTS user_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 文章表唯一约束
ALTER TABLE articles 
    DROP CONSTRAINT IF EXISTS articles_unique_constraint;
ALTER TABLE articles 
    ADD CONSTRAINT articles_unique_constraint 
    UNIQUE (username, topic, created_at);

-- 聊天会话表唯一约束
ALTER TABLE chat_sessions 
    DROP CONSTRAINT IF EXISTS chat_sessions_unique_constraint;
ALTER TABLE chat_sessions 
    ADD CONSTRAINT chat_sessions_unique_constraint 
    UNIQUE (username, created_at);

-- =============================================================================
-- 第四部分：应用数据表索引
-- =============================================================================

-- 文章表索引
CREATE INDEX IF NOT EXISTS idx_articles_username ON articles(username);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_tags ON articles USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_articles_metadata ON articles USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic);
CREATE INDEX IF NOT EXISTS idx_articles_model_type ON articles(model_type);

-- 全文搜索索引 (支持中文)
CREATE INDEX IF NOT EXISTS idx_articles_fulltext_topic ON articles 
    USING GIN(to_tsvector('simple', topic));
CREATE INDEX IF NOT EXISTS idx_articles_fulltext_content ON articles 
    USING GIN(to_tsvector('simple', article_content));
CREATE INDEX IF NOT EXISTS idx_articles_fulltext_summary ON articles 
    USING GIN(to_tsvector('simple', COALESCE(summary, '')));

-- 模糊搜索索引
CREATE INDEX IF NOT EXISTS idx_articles_topic_trgm ON articles 
    USING GIN(topic gin_trgm_ops);

-- 聊天会话表索引
CREATE INDEX IF NOT EXISTS idx_chat_sessions_username ON chat_sessions(username);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);

-- 用户配置表索引
CREATE INDEX IF NOT EXISTS idx_user_configs_username ON user_configs(username);

-- =============================================================================
-- 第五部分：触发器
-- =============================================================================

-- 文章表触发器
DROP TRIGGER IF EXISTS update_articles_updated_at ON articles;
CREATE TRIGGER update_articles_updated_at 
    BEFORE UPDATE ON articles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 聊天会话表触发器
DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;
CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 用户配置表触发器
DROP TRIGGER IF EXISTS update_user_configs_updated_at ON user_configs;
CREATE TRIGGER update_user_configs_updated_at 
    BEFORE UPDATE ON user_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 第六部分：实用函数和视图
-- =============================================================================

-- 全文搜索函数
CREATE OR REPLACE FUNCTION search_articles_fulltext(
    search_query TEXT,
    user_id TEXT DEFAULT NULL,
    limit_count INTEGER DEFAULT 20,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE(
    id UUID,
    username VARCHAR(100),
    topic VARCHAR(500),
    article_content TEXT,
    summary TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.username,
        a.topic,
        a.article_content,
        a.summary,
        a.tags,
        a.created_at,
        ts_rank(
            to_tsvector('simple', a.topic || ' ' || a.article_content || ' ' || COALESCE(a.summary, '')),
            to_tsquery('simple', search_query)
        ) as rank
    FROM articles a
    WHERE 
        to_tsvector('simple', a.topic || ' ' || a.article_content || ' ' || COALESCE(a.summary, '')) 
        @@ to_tsquery('simple', search_query)
        AND (user_id IS NULL OR a.username = user_id)
    ORDER BY rank DESC, a.created_at DESC
    LIMIT limit_count OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- 文章统计视图
CREATE OR REPLACE VIEW article_stats AS
SELECT 
    username,
    COUNT(*) as total_articles,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as articles_last_7_days,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as articles_last_30_days,
    AVG(LENGTH(article_content)) as avg_content_length,
    MAX(created_at) as last_article_date
FROM articles
GROUP BY username;

-- =============================================================================
-- 第七部分：表注释
-- =============================================================================

-- 认证系统表注释
COMMENT ON TABLE users IS '用户表：存储系统用户的基本信息';
COMMENT ON TABLE oauth_accounts IS 'OAuth账号绑定表：存储用户与第三方OAuth账号的绑定关系';
COMMENT ON COLUMN users.username IS '用户名，系统内唯一标识';
COMMENT ON COLUMN users.email IS '用户邮箱，可用于登录和找回密码';
COMMENT ON COLUMN users.password_hash IS '密码哈希，使用SHA256加密';
COMMENT ON COLUMN oauth_accounts.provider IS 'OAuth提供商：google, wechat等';
COMMENT ON COLUMN oauth_accounts.provider_user_id IS 'OAuth提供商的用户唯一标识';

-- 应用数据表注释
COMMENT ON TABLE articles IS '文章表：存储用户创作的文章内容';
COMMENT ON TABLE chat_sessions IS '聊天会话表：存储用户与AI的对话历史';
COMMENT ON TABLE user_configs IS '用户配置表：存储用户的个性化配置';

-- =============================================================================
-- 初始化完成
-- =============================================================================

-- 输出初始化信息
DO $$
BEGIN
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'SupaWriter 数据库初始化完成';
    RAISE NOTICE '=================================================';
    RAISE NOTICE '已创建表：';
    RAISE NOTICE '  - users (用户表)';
    RAISE NOTICE '  - oauth_accounts (OAuth绑定表)';
    RAISE NOTICE '  - articles (文章表)';
    RAISE NOTICE '  - chat_sessions (聊天会话表)';
    RAISE NOTICE '  - user_configs (用户配置表)';
    RAISE NOTICE '';
    RAISE NOTICE '默认管理员账号：';
    RAISE NOTICE '  用户名: admin';
    RAISE NOTICE '  密码: admin123';
    RAISE NOTICE '  邮箱: admin@supawriter.com';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  请立即修改默认管理员密码！';
    RAISE NOTICE '=================================================';
END $$;
