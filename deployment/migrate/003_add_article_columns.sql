-- =============================================================================
-- 添加 articles 表缺失的列
-- =============================================================================

-- 添加 status 列（生成状态）
ALTER TABLE articles 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft';

-- 添加 title 列（文章标题）
ALTER TABLE articles 
ADD COLUMN IF NOT EXISTS title VARCHAR(500);

-- 添加 content 列（文章内容，作为 article_content 的别名）
ALTER TABLE articles 
ADD COLUMN IF NOT EXISTS content TEXT;

-- 添加 outline 列（文章大纲）
ALTER TABLE articles 
ADD COLUMN IF NOT EXISTS outline JSONB;

-- 添加 completed_at 列（完成时间）
ALTER TABLE articles 
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title);

-- 迁移现有数据：将 article_content 复制到 content
UPDATE articles 
SET content = article_content 
WHERE content IS NULL AND article_content IS NOT NULL;

-- 添加注释
COMMENT ON COLUMN articles.status IS '文章状态: draft, generating, completed, failed';
COMMENT ON COLUMN articles.title IS '文章标题';
COMMENT ON COLUMN articles.content IS '文章内容（Markdown格式）';
COMMENT ON COLUMN articles.outline IS '文章大纲（JSON格式）';
COMMENT ON COLUMN articles.completed_at IS '文章完成时间';
