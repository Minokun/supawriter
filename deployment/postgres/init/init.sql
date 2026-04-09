-- =============================================================================
-- SupaWriter 完整数据库初始化脚本 v3.0
-- =============================================================================
-- 说明：此脚本可以从零开始完整重建 SupaWriter 数据库
-- 包含：认证系统、文章管理、聊天系统、用户设置、系统配置
--        P0功能（水印、评分、风格、引导）
--        P1功能（批量、Agent、预警、通知、订单、订阅、额度包）
--        P2功能（平台绑定、发布日志、知识库、团队协作、内容日历、API日志）
-- 创建时间：2026-02-02
-- 更新时间：2026-02-18
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
    membership_tier VARCHAR(20) DEFAULT 'free',  -- 会员等级: free, pro, ultra
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
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
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 第五部分：聊天系统表
-- =============================================================================

-- 聊天会话表
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
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

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
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- API 密钥管理表
CREATE TABLE IF NOT EXISTS user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    key_preview VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider)
);

-- 用户模型配置表
CREATE TABLE IF NOT EXISTS user_model_configs (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    chat_model VARCHAR(100) DEFAULT 'deepseek:deepseek-chat',
    writer_model VARCHAR(100) DEFAULT 'deepseek:deepseek-chat',
    embedding_model VARCHAR(100) DEFAULT 'openai:text-embedding-3-small',
    image_model VARCHAR(100) DEFAULT 'openai:dall-e-3',
    default_temperature DECIMAL(3,2) DEFAULT 0.7,
    default_max_tokens INTEGER DEFAULT 2000,
    default_top_p DECIMAL(3,2) DEFAULT 1.0,
    enable_streaming BOOLEAN DEFAULT TRUE,
    enable_thinking_process BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 用户偏好设置表
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    editor_font_size INTEGER DEFAULT 14,
    editor_theme VARCHAR(20) DEFAULT 'light',
    auto_save_interval INTEGER DEFAULT 30,
    default_article_style VARCHAR(50) DEFAULT 'professional',
    default_article_length VARCHAR(20) DEFAULT 'medium',
    default_language VARCHAR(10) DEFAULT 'zh-CN',
    sidebar_collapsed BOOLEAN DEFAULT FALSE,
    theme_mode VARCHAR(10) DEFAULT 'light',
    email_notifications BOOLEAN DEFAULT TRUE,
    task_complete_notification BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- LLM 提供商配置表
CREATE TABLE IF NOT EXISTS llm_providers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_id VARCHAR(50) NOT NULL,
    provider_name VARCHAR(100) NOT NULL,
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,
    models JSONB DEFAULT '[]',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 用户设置表索引
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_id ON user_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_provider ON user_api_keys(provider);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_is_active ON user_api_keys(is_active);

CREATE INDEX IF NOT EXISTS idx_llm_providers_user_id ON llm_providers(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_providers_provider_id ON llm_providers(provider_id);

CREATE INDEX IF NOT EXISTS idx_user_service_configs_user_id ON user_service_configs(user_id);

-- 用户主题表
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
-- 第七部分：P0 爆款基因植入功能表
-- =============================================================================

-- 1. 用户写作风格表（F5功能）
CREATE TABLE IF NOT EXISTS user_writing_styles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    style_profile JSONB NOT NULL DEFAULT '{}',
    -- style_profile 结构:
    -- {
    --   "tone": "语气风格",
    --   "sentence_style": "句式偏好",
    --   "paragraph_structure": "段落结构",
    --   "vocabulary": "用词特征",
    --   "opening_style": "开头风格",
    --   "closing_style": "结尾风格",
    --   "raw_analysis": "完整分析文本"
    -- }
    sample_filenames TEXT[] DEFAULT '{}',
    sample_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_writing_style UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_writing_styles_user_id
    ON user_writing_styles(user_id);

COMMENT ON TABLE user_writing_styles
    IS '用户写作风格配置，每个用户最多一条记录';

-- 2. 文章评分表（F4功能）
CREATE TABLE IF NOT EXISTS article_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    total_score INTEGER NOT NULL CHECK (total_score >= 0 AND total_score <= 100),
    level VARCHAR(20) NOT NULL CHECK (level IN ('excellent', 'good', 'average', 'poor')),
    summary TEXT NOT NULL DEFAULT '',
    dimensions JSONB NOT NULL DEFAULT '[]',
    -- dimensions 结构:
    -- [
    --   {
    --     "name": "readability",
    --     "label": "可读性",
    --     "score": 82,
    --     "weight": 0.3,
    --     "suggestions": ["建议1", "建议2"]
    --   },
    --   ...
    -- ]
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_article_score UNIQUE (article_id)
);

CREATE INDEX IF NOT EXISTS idx_article_scores_article_id
    ON article_scores(article_id);

COMMENT ON TABLE article_scores
    IS '文章质量评分，每篇文章一条评分记录';

-- 3. 用户引导状态表（F6功能）
CREATE TABLE IF NOT EXISTS user_onboarding (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    completed BOOLEAN DEFAULT FALSE,
    user_role VARCHAR(50) CHECK (user_role IN ('media_operator', 'marketer', 'freelancer', 'personal_ip', NULL)),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_onboarding UNIQUE (user_id)
);

COMMENT ON TABLE user_onboarding
    IS '新用户引导状态，记录用户是否完成引导及选择的角色';

-- =============================================================================
-- 第八部分：P1 付费价值构建功能表
-- =============================================================================

-- 1. 批量任务表
CREATE TABLE IF NOT EXISTS batch_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_count INTEGER NOT NULL,
    completed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'partial', 'cancelled')),
    settings JSONB NOT NULL DEFAULT '{}',
    topics TEXT[] NOT NULL,
    article_ids INTEGER[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_batch_tasks_user_id ON batch_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_batch_tasks_status ON batch_tasks(status);

-- 2. 写作Agent表
CREATE TABLE IF NOT EXISTS writing_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    domain_keywords TEXT[] NOT NULL DEFAULT '{}',
    frequency VARCHAR(50) NOT NULL DEFAULT 'daily',
    target_platform VARCHAR(20) DEFAULT 'wechat',
    model_type VARCHAR(50) DEFAULT 'deepseek',
    model_name VARCHAR(100) DEFAULT 'deepseek-chat',
    style_active BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    total_generated INTEGER DEFAULT 0,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_writing_agents_user_id ON writing_agents(user_id);
CREATE INDEX IF NOT EXISTS idx_writing_agents_next_run ON writing_agents(next_run_at) WHERE is_active = TRUE;

-- 3. Agent草稿表
CREATE TABLE IF NOT EXISTS agent_drafts (
    id SERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES writing_agents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE SET NULL,
    topic VARCHAR(500) NOT NULL,
    hotspot_source VARCHAR(50),
    score INTEGER,
    status VARCHAR(20) DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'discarded')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_drafts_agent_id ON agent_drafts(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_drafts_user_id ON agent_drafts(user_id);

-- 4. 用户预警配置表
CREATE TABLE IF NOT EXISTS user_alert_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keywords TEXT[] NOT NULL DEFAULT '{}',
    sources TEXT[] DEFAULT '{baidu,weibo,douyin,thepaper,36kr}',
    frequency VARCHAR(20) DEFAULT 'realtime'
        CHECK (frequency IN ('realtime', 'hourly', 'daily')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_alert_config UNIQUE (user_id)
);

-- 5. 通知表
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;

-- 6. 订单表
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('subscription', 'quota_pack')),
    plan VARCHAR(20),
    period VARCHAR(20),
    amount_cents INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')),
    payment_method VARCHAR(20),
    payment_id VARCHAR(100),
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_id ON orders(payment_id);

-- 7. 订阅表
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(20) NOT NULL CHECK (plan IN ('pro', 'ultra')),
    period VARCHAR(20) NOT NULL CHECK (period IN ('monthly', 'yearly')),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'cancelled', 'expired')),
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    auto_renew BOOLEAN DEFAULT TRUE,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_subscription UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expiry ON subscriptions(current_period_end) WHERE status = 'active';

-- 8. 额度包表
CREATE TABLE IF NOT EXISTS quota_packs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pack_type VARCHAR(20) NOT NULL,
    total_quota INTEGER NOT NULL,
    used_quota INTEGER DEFAULT 0,
    order_id UUID REFERENCES orders(id),
    purchased_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_quota_packs_user_id ON quota_packs(user_id);

-- 9. 平台转换日志表（用于数据看板统计）
CREATE TABLE IF NOT EXISTS platform_convert_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    article_id UUID,
    platform VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_convert_logs_user_date ON platform_convert_logs(user_id, created_at);

-- =============================================================================
-- 第九部分：P2 生态闭环功能表
-- =============================================================================

-- 1. 平台绑定表
CREATE TABLE IF NOT EXISTS platform_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('wechat_mp', 'toutiao', 'zhihu')),
    platform_user_id VARCHAR(255),
    platform_username VARCHAR(255),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_platform UNIQUE (user_id, platform)
);

-- 2. 发布日志表
CREATE TABLE IF NOT EXISTS publish_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'published', 'failed', 'scheduled')),
    external_id VARCHAR(255),
    external_url TEXT,
    error_message TEXT,
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_publish_logs_article ON publish_logs(article_id);

-- 3. 知识库文档表
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id INTEGER,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_size INTEGER NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    vectorized BOOLEAN DEFAULT FALSE,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_docs_user ON knowledge_documents(user_id);

-- 4. 文档分块表
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding_vector BYTEA,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_user ON document_chunks(user_id);

-- 5. 团队表
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    logo_url TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    max_members INTEGER DEFAULT 10,
    style_profile JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. 团队成员表
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_team_member UNIQUE (team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);

-- 7. 团队邀请表
CREATE TABLE IF NOT EXISTS team_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'editor',
    invited_by INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. 文章审批表
CREATE TABLE IF NOT EXISTS article_approvals (
    id SERIAL PRIMARY KEY,
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    submitted_by INTEGER NOT NULL REFERENCES users(id),
    reviewed_by INTEGER REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    review_comment TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_approvals_team ON article_approvals(team_id, status);

-- 9. 内容排期表
CREATE TABLE IF NOT EXISTS content_calendar (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE SET NULL,
    scheduled_date DATE NOT NULL,
    title VARCHAR(500),
    status VARCHAR(20) DEFAULT 'planned'
        CHECK (status IN ('planned', 'draft', 'scheduled', 'published')),
    platforms TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calendar_user_date ON content_calendar(user_id, scheduled_date);

-- 10. 节日/营销节点表
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    event_date DATE NOT NULL,
    event_type VARCHAR(20) NOT NULL
        CHECK (event_type IN ('holiday', 'solar_term', 'ecommerce', 'industry', 'custom')),
    description TEXT,
    content_suggestions TEXT[],
    is_recurring BOOLEAN DEFAULT TRUE,
    CONSTRAINT uq_event_date_name UNIQUE (event_date, name)
);

-- 11. API调用日志表
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    api_key_id INTEGER,
    endpoint VARCHAR(100) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_usage_user_date ON api_usage_logs(user_id, created_at);

-- 12. 添加team_id外键到knowledge_documents（团队知识库共享）
ALTER TABLE knowledge_documents
    ADD CONSTRAINT fk_knowledge_docs_team
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE;

-- =============================================================================
-- 第十部分：系统配置表
-- =============================================================================

-- 系统参数设置表
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(20) NOT NULL DEFAULT 'string',
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_system_settings_type ON system_settings(setting_type);
CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category);

-- =============================================================================
-- 第十一部分：视图和函数
-- =============================================================================

-- 用户完整信息视图
DROP VIEW IF EXISTS user_profile_view CASCADE;
CREATE VIEW user_profile_view AS
SELECT
    u.id,
    u.username,
    u.email,
    u.display_name,
    u.avatar_url,
    u.motto,
    u.is_active,
    u.membership_tier,
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
DROP VIEW IF EXISTS article_stats CASCADE;
CREATE VIEW article_stats AS
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
-- 第十二部分：表注释
-- =============================================================================

-- 认证系统
COMMENT ON TABLE users IS '用户表：存储系统用户的基本信息';
COMMENT ON COLUMN users.membership_tier IS '会员等级: free(免费), pro(专业), ultra(旗舰)';
COMMENT ON TABLE oauth_accounts IS 'OAuth账号绑定表：存储用户与第三方OAuth账号的绑定关系';
COMMENT ON COLUMN users.username IS '用户名，系统内唯一标识';
COMMENT ON COLUMN users.email IS '用户邮箱，可用于登录和找回密码';
COMMENT ON COLUMN users.password_hash IS '密码哈希，使用SHA256加密';
COMMENT ON COLUMN oauth_accounts.provider IS 'OAuth提供商：google, wechat等';
COMMENT ON COLUMN oauth_accounts.provider_user_id IS 'OAuth提供商的用户唯一标识';

-- 文章管理
COMMENT ON TABLE articles IS '文章表：存储用户创作的文章内容';
COMMENT ON COLUMN articles.status IS '文章状态: draft, generating, completed, failed';
COMMENT ON COLUMN articles.title IS '文章标题';
COMMENT ON COLUMN articles.content IS '文章内容（Markdown格式）';
COMMENT ON COLUMN articles.outline IS '文章大纲（JSON格式）';
COMMENT ON COLUMN articles.completed_at IS '文章完成时间';

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

-- P0 功能表
COMMENT ON TABLE user_writing_styles IS '用户写作风格配置（F5）：每个用户最多一条记录';
COMMENT ON TABLE article_scores IS '文章质量评分（F4）：每篇文章一条评分记录';
COMMENT ON TABLE user_onboarding IS '新用户引导状态（F6）：记录用户是否完成引导及选择的角色';

-- P1 功能表
COMMENT ON TABLE batch_tasks IS '批量任务表（F8）：Ultra用户批量生成文章';
COMMENT ON TABLE writing_agents IS '写作Agent表（F9）：自动定时生成文章的智能体';
COMMENT ON TABLE agent_drafts IS 'Agent草稿表（F9）：Agent生成的文章草稿';
COMMENT ON TABLE user_alert_configs IS '用户预警配置（F10）：热点预警设置';
COMMENT ON TABLE notifications IS '通知表（F10）：系统通知消息';
COMMENT ON TABLE orders IS '订单表（F12）：支付订单';
COMMENT ON TABLE subscriptions IS '订阅表（F12）：用户订阅记录';
COMMENT ON TABLE quota_packs IS '额度包表（F12）：用户购买额度的记录';
COMMENT ON TABLE platform_convert_logs IS '平台转换日志（F11）：用于数据看板统计';

-- P2 功能表
COMMENT ON TABLE platform_connections IS '平台绑定表（F13）：用户绑定的自媒体平台账号';
COMMENT ON TABLE publish_logs IS '发布日志表（F13）：文章发布到各平台的记录';
COMMENT ON TABLE knowledge_documents IS '知识库文档表（F14）：用户上传的知识库文件';
COMMENT ON TABLE document_chunks IS '文档分块表（F14）：文档的向量化分块';
COMMENT ON TABLE teams IS '团队表（F15）：团队信息';
COMMENT ON TABLE team_members IS '团队成员表（F15）：团队成员关系';
COMMENT ON TABLE team_invitations IS '团队邀请表（F15）：团队邀请记录';
COMMENT ON TABLE article_approvals IS '文章审批表（F15）：团队内容审批流程';
COMMENT ON TABLE content_calendar IS '内容排期表（F16）：内容发布日历';
COMMENT ON TABLE calendar_events IS '节日/营销节点表（F16）：营销日历';
COMMENT ON TABLE api_usage_logs IS 'API调用日志表（F17）：API使用统计';

-- =============================================================================
-- 第十三部分：初始数据
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
('article.process_config', '{"qwen":{"model":"qwen-vl-plus-2025-01-25"},"glm":{"model":"glm-4v"}}', 'json', 'article', '图片处理模型配置')
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
    ('openai', 'OpenAI', 'https://api.openai.com/v1',
     '["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo"]'::jsonb,
     'proprietary', 'OpenAI 官方 API', true),

    ('deepseek', 'DeepSeek', 'https://api.deepseek.com',
     '["deepseek-chat", "deepseek-reasoner"]'::jsonb,
     'proprietary', 'DeepSeek AI', true),

    ('kimi', 'Moonshot (Kimi)', 'https://api.moonshot.cn/v1',
     '["kimi-k2-0905-preview", "kimi-k2-turbo-preview", "kimi-k2.5"]'::jsonb,
     'proprietary', 'Moonshot AI (Kimi)', true),

    ('dashscope', 'DashScope (通义千问)', 'https://dashscope.aliyuncs.com/compatible-mode/v1',
     '["qwen-2.5b-instruct-25k", "qwen-2.5b-thinking-25k", "qwen-3-5b-thinking-25k", "qwen-3.5b-instruct-25k", "qwen-coder-4b-a35b-instruct", "qwen-coder-plus", "qwen-plus-2025-07-28"]'::jsonb,
     'proprietary', '阿里云通义千问', true),

    ('glm', '智谱 GLM', 'https://open.bigmodel.cn/api/paas/v4/',
     '["GLM-4.7"]'::jsonb,
     'proprietary', '智谱 AI', true),

    ('gitee', 'Gitee AI', 'https://ai.gitee.com/v1',
     '["kimi-k2-instruct", "Qwen-2.5B-A22B-Instruct-25K", "qwen-coder-4b-a35b-instruct"]'::jsonb,
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
     '["qwen-2.5B"]'::jsonb,
     'self_hosted', 'FastGPT 自建', true),

    ('xinference', 'Xinference', 'http://10.10.10.90:9997/v1',
     '["qwen-2.5B", "deepseek-r1-0528-qwen-2.5B"]'::jsonb,
     'self_hosted', 'Xinference 自建', false)
ON CONFLICT (provider_id) DO NOTHING;

-- =============================================================================
-- 第十四部分：性能优化
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
ANALYZE user_writing_styles;
ANALYZE article_scores;
ANALYZE user_onboarding;
ANALYZE batch_tasks;
ANALYZE writing_agents;
ANALYZE agent_drafts;
ANALYZE user_alert_configs;
ANALYZE notifications;
ANALYZE orders;
ANALYZE subscriptions;
ANALYZE quota_packs;
ANALYZE platform_convert_logs;
ANALYZE platform_connections;
ANALYZE publish_logs;
ANALYZE knowledge_documents;
ANALYZE document_chunks;
ANALYZE teams;
ANALYZE team_members;
ANALYZE team_invitations;
ANALYZE article_approvals;
ANALYZE content_calendar;
ANALYZE calendar_events;
ANALYZE api_usage_logs;
ANALYZE llm_provider_templates;
ANALYZE system_settings;

-- =============================================================================
-- 第十五部分：初始化完成
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'SupaWriter 数据库初始化完成 v3.0';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE '已创建表：';
    RAISE NOTICE ' 认证系统:';
    RAISE NOTICE '    - users (用户表) [包含: membership_tier, avatar_source]';
    RAISE NOTICE '    - oauth_accounts (OAuth绑定表)';
    RAISE NOTICE '';
    RAISE NOTICE ' 文章管理:';
    RAISE NOTICE '    - articles (文章表) [包含: status, title, content, outline, completed_at]';
    RAISE NOTICE '';
    RAISE NOTICE ' 聊天系统:';
    RAISE NOTICE '    - chat_sessions (聊天会话表)';
    RAISE NOTICE '    - chat_messages (聊天消息表)';
    RAISE NOTICE '';
    RAISE NOTICE ' 用户配置:';
    RAISE NOTICE '    - user_configs (用户配置表-旧版)';
    RAISE NOTICE '    - user_api_keys (API密钥表)';
    RAISE NOTICE '    - user_model_configs (模型配置表)';
    RAISE NOTICE '    - user_preferences (偏好设置表)';
    RAISE NOTICE '    - llm_providers (LLM提供商表)';
    RAISE NOTICE '    - user_service_configs (服务配置表)';
    RAISE NOTICE '    - user_topics (用户主题表-推文选题)';
    RAISE NOTICE '    - llm_provider_templates (LLM提供商模板表-系统级)';
    RAISE NOTICE '';
    RAISE NOTICE ' 系统配置:';
    RAISE NOTICE '    - system_settings (系统设置表)';
    RAISE NOTICE '';
    RAISE NOTICE ' P0 爆款基因植入功能:';
    RAISE NOTICE '    - user_writing_styles (用户写作风格 - F5)';
    RAISE NOTICE '    - article_scores (文章质量评分 - F4)';
    RAISE NOTICE '    - user_onboarding (新用户引导 - F6)';
    RAISE NOTICE '';
    RAISE NOTICE ' P1 付费价值构建功能:';
    RAISE NOTICE '    - batch_tasks (批量任务 - F8)';
    RAISE NOTICE '    - writing_agents (写作Agent - F9)';
    RAISE NOTICE '    - agent_drafts (Agent草稿 - F9)';
    RAISE NOTICE '    - user_alert_configs (用户预警 - F10)';
    RAISE NOTICE '    - notifications (通知 - F10)';
    RAISE NOTICE '    - orders (订单 - F12)';
    RAISE NOTICE '    - subscriptions (订阅 - F12)';
    RAISE NOTICE '    - quota_packs (额度包 - F12)';
    RAISE NOTICE '    - platform_convert_logs (平台转换日志 - F11)';
    RAISE NOTICE '';
    RAISE NOTICE ' P2 生态闭环功能:';
    RAISE NOTICE '    - platform_connections (平台绑定 - F13)';
    RAISE NOTICE '    - publish_logs (发布日志 - F13)';
    RAISE NOTICE '    - knowledge_documents (知识库文档 - F14)';
    RAISE NOTICE '    - document_chunks (文档分块 - F14)';
    RAISE NOTICE '    - teams (团队 - F15)';
    RAISE NOTICE '    - team_members (团队成员 - F15)';
    RAISE NOTICE '    - team_invitations (团队邀请 - F15)';
    RAISE NOTICE '    - article_approvals (文章审批 - F15)';
    RAISE NOTICE '    - content_calendar (内容排期 - F16)';
    RAISE NOTICE '    - calendar_events (营销日历 - F16)';
    RAISE NOTICE '    - api_usage_logs (API日志 - F17)';
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
    RAISE NOTICE '';
END $$;
