-- Migration 009: P1 付费价值构建功能
-- Date: 2026-02-15
-- Features: 批量生成、写作Agent、热点预警、通知、订单、订阅、额度包、平台转换日志

BEGIN;

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
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
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
    article_id INTEGER,
    platform VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_convert_logs_user_date ON platform_convert_logs(user_id, created_at);

COMMIT;
