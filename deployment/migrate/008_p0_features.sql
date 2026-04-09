-- Migration 008: P0 爆款基因植入功能
-- Date: 2026-02-15
-- Features: 用户写作风格、文章评分、用户引导
-- Related: docs/plans/2026-02-15-p0-technical-design.md

BEGIN;

-- ============================================
-- 1. 用户写作风格表
-- ============================================
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

-- ============================================
-- 2. 文章评分表
-- ============================================
CREATE TABLE IF NOT EXISTS article_scores (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
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

-- ============================================
-- 3. 用户引导状态表
-- ============================================
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

COMMIT;
