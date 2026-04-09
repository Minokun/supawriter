-- =============================================================================
-- SupaWriter 完整数据库初始化脚本 v2.1
-- =============================================================================
-- 说明：此脚本可以从零开始完整重建 SupaWriter 数据库
-- 包含：认证系统、文章管理、聊天系统、用户设置、系统配置
-- 创建时间：2026-02-02
-- 更新时间：2026-02-10
-- 变更记录：
--   v2.1 (2026-02-10):
--     - users 表新增 avatar_source 字段（跟踪头像来源）
--     - articles 表新增 status, title, content, outline, completed_at 字段
--     - 新增 user_topics 表（用户主题/推文选题）
--     - 新增 llm_provider_templates 表（系统级 LLM 提供商模板）
--     - 初始化 11 个 LLM 提供商模板数据
--   v2.0 (2026-02-02): 初始版本
-- =============================================================================

-- =============================================================================
-- 第一部分：PostgreSQL 扩展
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";           -- UUID 生成
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";  -- 性能统计
CREATE EXTENSION IF NOT EXISTS "pg_trgm";             -- 模糊搜索（三元组）

-- =============================================================================
-- 第二部分：全局函数
-- =============================================================================

-- 自动更新 updated_at 字段的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 第三部分：认证系统表
-- =============================================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    display_name VARCHAR(100),
    avatar_url TEXT,
    avatar_source VARCHAR(20),  -- 头像来源: google, wechat, manual
    motto VARCHAR(200) DEFAULT '创作改变世界',
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    membership_tier VARCHAR(20) DEFAULT 'free',  -- 会员等级: free, pro, ultra
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_avatar_source CHECK (avatar_source IN ('google', 'wechat', 'manual', NULL) OR avatar_source IS NULL)
);

-- OAuth 账号绑定表
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    extra_data JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);

-- 认证系统索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);
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

-- =============================================================================
-- 第四部分：文章管理表
-- =============================================================================

-- 文章表
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username VARCHAR(100) NOT NULL,
    topic VARCHAR(500) NOT NULL,
    article_content TEXT NOT NULL,
    content TEXT,  -- 文章内容（Markdown格式），与 article_content 同步
    title VARCHAR(500),  -- 文章标题
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
    status VARCHAR(20) DEFAULT 'draft',  -- 文章状态: draft, generating, completed, failed
    outline JSONB,  -- 文章大纲（JSON格式）
    completed_at TIMESTAMPTZ,  -- 文章完成时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 文章表索引
CREATE INDEX IF NOT EXISTS idx_articles_user_id ON articles(user_id);
CREATE INDEX IF NOT EXISTS idx_articles_username ON articles(username);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_tags ON articles USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_articles_metadata ON articles USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic);
CREATE INDEX IF NOT EXISTS idx_articles_model_type ON articles(model_type);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_articles_fulltext_topic ON articles 
    USING GIN(to_tsvector('simple', topic));
CREATE INDEX IF NOT EXISTS idx_articles_fulltext_content ON articles 
    USING GIN(to_tsvector('simple', article_content));
CREATE INDEX IF NOT EXISTS idx_articles_fulltext_summary ON articles 
    USING GIN(to_tsvector('simple', COALESCE(summary, '')));

-- 模糊搜索索引
CREATE INDEX IF NOT EXISTS idx_articles_topic_trgm ON articles 
    USING GIN(topic gin_trgm_ops);

-- 文章表触发器
DROP TRIGGER IF EXISTS update_articles_updated_at ON articles;
CREATE TRIGGER update_articles_updated_at 
    BEFORE UPDATE ON articles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 第五部分：聊天系统表
-- =============================================================================

-- 聊天会话表（已包含 user_id 和 model 列）
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username VARCHAR(100),
    title VARCHAR(500),
    model VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    thinking TEXT,
    model VARCHAR(100),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 聊天系统索引
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_username ON chat_sessions(username);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_created ON chat_sessions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_timestamp ON chat_messages(session_id, timestamp ASC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created_role ON chat_messages(session_id, timestamp, role);

-- 聊天系统触发器
DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;
CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 第六部分：用户配置表
-- =============================================================================

-- 用户配置表（旧版，保留兼容性）
CREATE TABLE IF NOT EXISTS user_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_configs_username ON user_configs(username);

DROP TRIGGER IF EXISTS update_user_configs_updated_at ON user_configs;
CREATE TRIGGER update_user_configs_updated_at 
    BEFORE UPDATE ON user_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 第七部分：用户设置表（新版）
-- =============================================================================

-- API 密钥管理表
CREATE TABLE IF NOT EXISTS user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    key_preview VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- 用户模型配置表
CREATE TABLE IF NOT EXISTS user_model_configs (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    chat_model VARCHAR(100) DEFAULT 'deepseek/deepseek-chat',
    writer_model VARCHAR(100) DEFAULT 'deepseek/deepseek-chat',
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    image_model VARCHAR(100) DEFAULT 'dall-e-3',
    default_temperature DECIMAL(3,2) DEFAULT 0.7,
    default_max_tokens INTEGER DEFAULT 2000,
    default_top_p DECIMAL(3,2) DEFAULT 1.0,
    enable_streaming BOOLEAN DEFAULT TRUE,
    enable_thinking_process BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户偏好设置表
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    editor_font_size INTEGER DEFAULT 14,
    editor_theme VARCHAR(20) DEFAULT 'vs-light',
    auto_save_interval INTEGER DEFAULT 30,
    default_article_style VARCHAR(50) DEFAULT 'professional',
    default_article_length VARCHAR(20) DEFAULT 'medium',
    default_language VARCHAR(10) DEFAULT 'zh-CN',
    sidebar_collapsed BOOLEAN DEFAULT FALSE,
    theme_mode VARCHAR(10) DEFAULT 'light',
    email_notifications BOOLEAN DEFAULT TRUE,
    task_complete_notification BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- LLM 提供商配置表
CREATE TABLE IF NOT EXISTS llm_providers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider_id VARCHAR(50) NOT NULL,
    provider_name VARCHAR(100) NOT NULL,
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,
    models JSONB DEFAULT '[]',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider_id)
);

-- 用户服务配置表（七牛云、SERPER等）
CREATE TABLE IF NOT EXISTS user_service_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    qiniu_domain VARCHAR(255),
    qiniu_folder VARCHAR(255),
    qiniu_access_key_encrypted TEXT,
    qiniu_secret_key_encrypted TEXT,
    qiniu_region VARCHAR(10),
    serper_api_key_encrypted TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户设置表索引
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_id ON user_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_provider ON user_api_keys(provider);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_provider ON user_api_keys(user_id, provider);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_is_active ON user_api_keys(is_active);

CREATE INDEX IF NOT EXISTS idx_llm_providers_user_id ON llm_providers(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_providers_provider_id ON llm_providers(provider_id);

CREATE INDEX IF NOT EXISTS idx_user_service_configs_user_id ON user_service_configs(user_id);

-- 用户主题表（推文选题）
CREATE TABLE IF NOT EXISTS user_topics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_name VARCHAR(200) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, topic_name)
);

CREATE INDEX IF NOT EXISTS idx_user_topics_user_id ON user_topics(user_id);
CREATE INDEX IF NOT EXISTS idx_user_topics_created_at ON user_topics(created_at DESC);

DROP TRIGGER IF EXISTS update_user_topics_updated_at ON user_topics;
CREATE TRIGGER update_user_topics_updated_at
    BEFORE UPDATE ON user_topics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- LLM 提供商模板表（系统级）
CREATE TABLE IF NOT EXISTS llm_provider_templates (
    id SERIAL PRIMARY KEY,
    provider_id VARCHAR(50) NOT NULL UNIQUE,
    provider_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    base_url TEXT NOT NULL,
    default_models JSONB DEFAULT '[]',
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    icon_url TEXT,
    official_docs_url TEXT,
    requires_api_key BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_provider_templates_provider_id ON llm_provider_templates(provider_id);
CREATE INDEX IF NOT EXISTS idx_llm_provider_templates_category ON llm_provider_templates(category);
CREATE INDEX IF NOT EXISTS idx_llm_provider_templates_active ON llm_provider_templates(is_active);

DROP TRIGGER IF EXISTS update_llm_provider_templates_updated_at ON llm_provider_templates;
CREATE TRIGGER update_llm_provider_templates_updated_at
    BEFORE UPDATE ON llm_provider_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 第八部分：系统配置表
-- =============================================================================

-- 系统参数设置表
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(20) NOT NULL DEFAULT 'string',
    category VARCHAR(50) DEFAULT 'general',  -- 配置分类: search, article, embedding, storage, quota
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_system_settings_type ON system_settings(setting_type);
CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category);

-- =============================================================================
-- 第九部分：视图和函数
-- =============================================================================

-- 用户完整信息视图
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

-- =============================================================================
-- 第十部分：表注释
-- =============================================================================

-- 认证系统
COMMENT ON TABLE users IS '用户表：存储系统用户的基本信息';
COMMENT ON COLUMN users.membership_tier IS '会员等级: free(免费), pro(专业), ultra(旗舰)';
COMMENT ON TABLE oauth_accounts IS 'OAuth账号绑定表：存储用户与第三方OAuth账号的绑定关系';

-- 文章管理
COMMENT ON TABLE articles IS '文章表：存储用户创作的文章内容';

-- 聊天系统
COMMENT ON TABLE chat_sessions IS '聊天会话表：存储用户与AI的对话会话';
COMMENT ON TABLE chat_messages IS '聊天消息表：存储用户与AI的单条对话消息';
COMMENT ON COLUMN chat_messages.thinking IS 'AI思考过程（某些模型如deepseek-r1会返回）';

-- 用户配置
COMMENT ON TABLE user_configs IS '用户配置表（旧版）：存储用户的个性化配置';
COMMENT ON TABLE user_api_keys IS '用户 API 密钥（加密存储）';
COMMENT ON TABLE user_model_configs IS '用户 AI 模型配置';
COMMENT ON TABLE user_preferences IS '用户偏好设置';
COMMENT ON TABLE llm_providers IS 'LLM 提供商配置表（用户级别）';
COMMENT ON TABLE user_service_configs IS '用户其他服务配置表（七牛云、SERPER等）';
COMMENT ON TABLE user_topics IS '用户主题表：保存用户自定义的研究主题（推文选题）';
COMMENT ON TABLE llm_provider_templates IS '系统级 LLM 提供商模板表：存储所有可用的提供商配置';

-- 系统配置
COMMENT ON TABLE system_settings IS '系统参数设置表（存储全局配置）';

-- =============================================================================
-- 第十一部分：初始数据
-- =============================================================================

-- 插入默认管理员账号（密码为: admin123）
INSERT INTO users (username, email, password_hash, display_name, is_superuser, membership_tier)
VALUES ('admin', 'admin@supawriter.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', '管理员', TRUE, 'ultra')
ON CONFLICT (username) DO NOTHING;

-- 系统配置种子数据
-- 搜索配置
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('search.default_spider_num', '20', 'integer', 'search', 'DDGS 搜索结果数量'),
('search.serper_api_key', '', 'string', 'search', 'Serper 搜索 API Key')
ON CONFLICT (setting_key) DO NOTHING;

-- 文章生成配置
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('article.default_enable_images', 'true', 'boolean', 'article', '是否默认启用图片'),
('article.image_embedding_method', 'direct_embedding', 'string', 'article', '图片嵌入方式: direct_embedding 或 multimodal'),
('article.process_image_type', 'glm', 'string', 'article', '图片处理模型类型: glm 或 qwen'),
('article.process_config', '{"qwen":{"model":"qwen-vl-plus-2025-01-25"},"glm":{"model":"glm-4.5v"}}', 'json', 'article', '图片处理模型配置')
ON CONFLICT (setting_key) DO NOTHING;

-- Embedding 配置
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('embedding.default_provider', 'gitee', 'string', 'embedding', '默认 Embedding 提供商'),
('embedding.model', 'jina-embeddings-v4', 'string', 'embedding', 'Embedding 模型'),
('embedding.dimension', '2048', 'integer', 'embedding', 'Embedding 维度'),
('embedding.timeout', '10', 'integer', 'embedding', 'Embedding 超时时间(秒)'),
('embedding.gitee.base_url', 'https://ai.gitee.com/v1', 'string', 'embedding', 'Gitee Embedding API 地址'),
('embedding.gitee.api_key', '', 'string', 'embedding', 'Gitee Embedding API Key'),
('embedding.jina.base_url', '', 'string', 'embedding', 'Jina Embedding API 地址'),
('embedding.jina.api_key', '', 'string', 'embedding', 'Jina Embedding API Key'),
('embedding.jina.model', 'jina-embeddings-v4', 'string', 'embedding', 'Jina Embedding 模型')
ON CONFLICT (setting_key) DO NOTHING;

-- 七牛云存储配置
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('qiniu.domain', '', 'string', 'storage', '七牛云域名'),
('qiniu.folder', '', 'string', 'storage', '七牛云存储桶目录'),
('qiniu.access_key', '', 'string', 'storage', '七牛云 Access Key'),
('qiniu.secret_key', '', 'string', 'storage', '七牛云 Secret Key'),
('qiniu.region', 'z2', 'string', 'storage', '七牛云存储区域')
ON CONFLICT (setting_key) DO NOTHING;

-- 会员等级配额配置 - free
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('quota.free.article_daily_limit', '10', 'integer', 'quota', '免费用户每日文章限额'),
('quota.free.article_monthly_limit', '100', 'integer', 'quota', '免费用户每月文章限额'),
('quota.free.spider_num', '10', 'integer', 'quota', '免费用户搜索数量'),
('quota.free.api_daily_limit', '100', 'integer', 'quota', '免费用户每日API调用限额'),
('quota.free.storage_limit_mb', '500', 'integer', 'quota', '免费用户存储限额(MB)')
ON CONFLICT (setting_key) DO NOTHING;

-- 会员等级配额配置 - pro
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('quota.pro.article_daily_limit', '50', 'integer', 'quota', 'Pro用户每日文章限额'),
('quota.pro.article_monthly_limit', '500', 'integer', 'quota', 'Pro用户每月文章限额'),
('quota.pro.spider_num', '30', 'integer', 'quota', 'Pro用户搜索数量'),
('quota.pro.api_daily_limit', '1000', 'integer', 'quota', 'Pro用户每日API调用限额'),
('quota.pro.storage_limit_mb', '5000', 'integer', 'quota', 'Pro用户存储限额(MB)')
ON CONFLICT (setting_key) DO NOTHING;

-- 会员等级配额配置 - ultra
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('quota.ultra.article_daily_limit', '200', 'integer', 'quota', 'Ultra用户每日文章限额'),
('quota.ultra.article_monthly_limit', '2000', 'integer', 'quota', 'Ultra用户每月文章限额'),
('quota.ultra.spider_num', '50', 'integer', 'quota', 'Ultra用户搜索数量'),
('quota.ultra.api_daily_limit', '10000', 'integer', 'quota', 'Ultra用户每日API调用限额'),
('quota.ultra.storage_limit_mb', '50000', 'integer', 'quota', 'Ultra用户存储限额(MB)')
ON CONFLICT (setting_key) DO NOTHING;

-- LLM 提供商模板初始数据（11个提供商）
INSERT INTO llm_provider_templates (
    provider_id, provider_name, base_url, default_models, category, description, requires_api_key
) VALUES
    ('openai', 'OpenAI', 'https://openai.sevnday.top/v1',
     '["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-4.1-mini", "gpt-4o"]'::jsonb,
     'proprietary', 'OpenAI 官方 API', true),
    ('deepseek', 'DeepSeek', 'https://api.deepseek.com',
     '["deepseek-chat", "deepseek-reasoner"]'::jsonb,
     'proprietary', 'DeepSeek AI', true),
    ('kimi', 'Moonshot (Kimi)', 'https://api.moonshot.cn/v1',
     '["kimi-k2-0905-preview", "kimi-k2-turbo-preview", "kimi-k2.5"]'::jsonb,
     'proprietary', 'Moonshot AI (Kimi)', true),
    ('dashscope', 'DashScope (通义千问)', 'https://dashscope.aliyuncs.com/compatible-mode/v1',
     '["qwen3-235b-a22b-instruct-2507", "qwen3-235b-a22b-thinking-2507", "qwen3-30b-a3b-thinking-2507", "qwen3-30b-a3b-instruct-2507", "qwen3-coder-480b-a35b-instruct", "qwen3-coder-plus", "qwen-plus-2025-07-28"]'::jsonb,
     'proprietary', '阿里云通义千问', true),
    ('glm', '智谱 GLM', 'https://open.bigmodel.cn/api/paas/v4/',
     '["GLM-4.7"]'::jsonb,
     'proprietary', '智谱 AI', true),
    ('gitee', 'Gitee AI', 'https://ai.gitee.com/v1',
     '["kimi-k2-instruct", "Qwen3-235B-A22B-Instruct-2507", "qwen3-coder-480b-a35b-instruct"]'::jsonb,
     'proprietary', 'Gitee AI 平台', true),
    ('longcat', 'LongCat', 'https://api.longcat.chat/openai/v1',
     '["LongCat-Flash-Chat", "LongCat-Flash-Thinking"]'::jsonb,
     'proprietary', 'LongCat AI', true),
    ('minimax', 'MiniMax', 'https://api.minimaxi.com/v1',
     '["MiniMax-M2"]'::jsonb,
     'proprietary', 'MiniMax AI', true),
    ('nvidia', 'NVIDIA', 'https://integrate.api.nvidia.com/v1',
     '["z-ai/glm4.7"]'::jsonb,
     'proprietary', 'NVIDIA AI', true),
    ('fastgpt', 'FastGPT', 'http://10.10.10.90:3000/api/v1',
     '["qwen3-32B"]'::jsonb,
     'self_hosted', 'FastGPT 自建', true),
    ('xinference', 'Xinference', 'http://10.10.10.90:9997/v1',
     '["qwen3", "deepseek-r1-0528-qwen3"]'::jsonb,
     'self_hosted', 'Xinference 自建', false)
ON CONFLICT (provider_id) DO NOTHING;

-- =============================================================================
-- 第十二部分：性能优化
-- =============================================================================

-- 分析表以更新统计信息
ANALYZE users;
ANALYZE oauth_accounts;
ANALYZE articles;
ANALYZE chat_sessions;
ANALYZE chat_messages;
ANALYZE user_configs;
ANALYZE user_api_keys;
ANALYZE user_model_configs;
ANALYZE user_preferences;
ANALYZE llm_providers;
ANALYZE user_service_configs;
ANALYZE user_topics;
ANALYZE llm_provider_templates;
ANALYZE system_settings;

-- =============================================================================
-- 初始化完成
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'SupaWriter 数据库初始化完成 v2.1';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE '';
    RAISE NOTICE '已创建表：';
    RAISE NOTICE '  认证系统:';
    RAISE NOTICE '    - users (用户表) [新增: avatar_source]';
    RAISE NOTICE '    - oauth_accounts (OAuth绑定表)';
    RAISE NOTICE '';
    RAISE NOTICE '  文章管理:';
    RAISE NOTICE '    - articles (文章表) [新增: status, title, content, outline, completed_at]';
    RAISE NOTICE '';
    RAISE NOTICE '  聊天系统:';
    RAISE NOTICE '    - chat_sessions (聊天会话表)';
    RAISE NOTICE '    - chat_messages (聊天消息表)';
    RAISE NOTICE '';
    RAISE NOTICE '  用户配置:';
    RAISE NOTICE '    - user_configs (用户配置表-旧版)';
    RAISE NOTICE '    - user_api_keys (API密钥表)';
    RAISE NOTICE '    - user_model_configs (模型配置表)';
    RAISE NOTICE '    - user_preferences (偏好设置表)';
    RAISE NOTICE '    - llm_providers (LLM提供商表)';
    RAISE NOTICE '    - user_service_configs (服务配置表)';
    RAISE NOTICE '    - user_topics (用户主题表-推文选题) [新增]';
    RAISE NOTICE '';
    RAISE NOTICE '  系统配置:';
    RAISE NOTICE '    - system_settings (系统设置表)';
    RAISE NOTICE '    - llm_provider_templates (LLM提供商模板表-系统级) [新增]';
    RAISE NOTICE '';
    RAISE NOTICE '已创建视图：';
    RAISE NOTICE '    - user_profile_view (用户完整信息视图)';
    RAISE NOTICE '    - article_stats (文章统计视图)';
    RAISE NOTICE '';
    RAISE NOTICE '已创建函数：';
    RAISE NOTICE '    - update_updated_at_column() (自动更新时间戳)';
    RAISE NOTICE '    - search_articles_fulltext() (全文搜索)';
    RAISE NOTICE '';
    RAISE NOTICE '初始数据：';
    RAISE NOTICE '    - 11个LLM提供商模板 (openai, deepseek, kimi, dashscope, glm, gitee, longcat, minimax, nvidia, fastgpt, xinference)';
    RAISE NOTICE '';
    RAISE NOTICE '默认管理员账号：';
    RAISE NOTICE '    用户名: admin';
    RAISE NOTICE '    密码: admin123';
    RAISE NOTICE '    邮箱: admin@supawriter.com';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  安全提示：';
    RAISE NOTICE '    1. 请立即修改默认管理员密码！';
    RAISE NOTICE '    2. 敏感配置（API密钥等）应使用加密存储';
    RAISE NOTICE '    3. 生产环境请配置适当的数据库访问权限';
    RAISE NOTICE '';
    RAISE NOTICE '=============================================================================';
END $$;
