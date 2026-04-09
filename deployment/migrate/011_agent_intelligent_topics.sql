-- Migration 011: Agent智能选题优化
-- Date: 2025-01-20
-- Features: Agent绑定主题、新闻源配置、执行频率、每次生成文章数、草稿评分

BEGIN;

-- 1. WritingAgent新增字段
ALTER TABLE writing_agents
    ADD COLUMN IF NOT EXISTS topic_id INTEGER REFERENCES user_topics(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS news_sources JSONB,
    ADD COLUMN IF NOT EXISTS schedule_cron VARCHAR(20) NOT NULL DEFAULT '1h',
    ADD COLUMN IF NOT EXISTS article_count INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_writing_agents_topic ON writing_agents(topic_id);

-- 2. AgentDraft新增评分字段
ALTER TABLE agent_drafts
    ADD COLUMN IF NOT EXISTS relevance_score INTEGER,
    ADD COLUMN IF NOT EXISTS value_score INTEGER;

COMMIT;
