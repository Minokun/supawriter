-- SupaWriter 数据库初始化脚本
-- 创建数据库和用户，设置权限

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索

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

-- 添加唯一约束，防止重复迁移数据
-- 为articles表添加唯一约束：username + topic + created_at
ALTER TABLE articles 
    DROP CONSTRAINT IF EXISTS articles_unique_constraint;
ALTER TABLE articles 
    ADD CONSTRAINT articles_unique_constraint 
    UNIQUE (username, topic, created_at);

-- 为chat_sessions表添加唯一约束：username + created_at
ALTER TABLE chat_sessions 
    DROP CONSTRAINT IF EXISTS chat_sessions_unique_constraint;
ALTER TABLE chat_sessions 
    ADD CONSTRAINT chat_sessions_unique_constraint 
    UNIQUE (username, created_at);

-- 创建索引
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

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为表添加更新时间触发器
CREATE TRIGGER update_articles_updated_at 
    BEFORE UPDATE ON articles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_configs_updated_at 
    BEFORE UPDATE ON user_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建全文搜索函数
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

-- 创建统计视图
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

-- 插入示例数据 (可选)
-- INSERT INTO articles (username, topic, article_content, summary, tags) VALUES
-- ('demo_user', '人工智能的发展趋势', '人工智能正在快速发展...', '本文探讨了AI的未来发展方向', ARRAY['AI', '技术', '未来']);

-- 创建数据库用户和权限设置
-- 注意：这些命令需要在容器启动后手动执行，或者通过环境变量设置
-- CREATE USER supawriter_app WITH PASSWORD 'your_app_password';
-- GRANT CONNECT ON DATABASE supawriter TO supawriter_app;
-- GRANT USAGE ON SCHEMA public TO supawriter_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO supawriter_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO supawriter_app;

-- 设置默认权限
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO supawriter_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO supawriter_app;
