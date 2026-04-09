-- =============================================================================
-- 004: 系统配置统一化迁移
-- 将散落在 .env / 硬编码中的业务配置统一到 system_settings 表
-- 添加会员等级支持
-- =============================================================================

-- 1. users 表添加 membership_tier 字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS membership_tier VARCHAR(20) DEFAULT 'free';
COMMENT ON COLUMN users.membership_tier IS '会员等级: free(免费), pro(专业), ultra(旗舰)';

-- 2. system_settings 表添加 category 字段
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'general';
CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category);

-- 3. 更新已有记录的 category（如果之前没有 category）
UPDATE system_settings SET category = 'search' WHERE setting_key LIKE 'serper.%' AND (category IS NULL OR category = 'general');
UPDATE system_settings SET category = 'embedding' WHERE setting_key LIKE 'embedding.%' AND (category IS NULL OR category = 'general');
UPDATE system_settings SET category = 'storage' WHERE setting_key LIKE 'qiniu.%' AND (category IS NULL OR category = 'general');

-- 4. 迁移旧 key: serper.api_key → search.serper_api_key（保留旧 key 兼容）
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description)
SELECT 'search.serper_api_key', setting_value, 'string', 'search', 'Serper 搜索 API Key'
FROM system_settings WHERE setting_key = 'serper.api_key'
ON CONFLICT (setting_key) DO NOTHING;

-- 5. 插入新的搜索配置
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('search.default_spider_num', '20', 'integer', 'search', 'DDGS 搜索结果数量')
ON CONFLICT (setting_key) DO NOTHING;

-- 6. 插入文章生成配置
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('article.default_enable_images', 'true', 'boolean', 'article', '是否默认启用图片'),
('article.image_embedding_method', 'direct_embedding', 'string', 'article', '图片嵌入方式: direct_embedding 或 multimodal'),
('article.process_image_type', 'glm', 'string', 'article', '图片处理模型类型: glm 或 qwen'),
('article.process_config', '{"qwen":{"model":"qwen-vl-plus-2025-01-25"},"glm":{"model":"glm-4.5v"}}', 'json', 'article', '图片处理模型配置')
ON CONFLICT (setting_key) DO NOTHING;

-- 7. 补充 Embedding 配置（部分可能已存在）
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('embedding.model', 'jina-embeddings-v4', 'string', 'embedding', 'Embedding 模型'),
('embedding.dimension', '2048', 'integer', 'embedding', 'Embedding 维度'),
('embedding.timeout', '10', 'integer', 'embedding', 'Embedding 超时时间(秒)'),
('embedding.gitee.base_url', 'https://ai.gitee.com/v1', 'string', 'embedding', 'Gitee Embedding API 地址'),
('embedding.gitee.api_key', '', 'string', 'embedding', 'Gitee Embedding API Key')
ON CONFLICT (setting_key) DO NOTHING;

-- 8. 会员等级配额配置 - free
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('quota.free.article_daily_limit', '10', 'integer', 'quota', '免费用户每日文章限额'),
('quota.free.article_monthly_limit', '100', 'integer', 'quota', '免费用户每月文章限额'),
('quota.free.spider_num', '10', 'integer', 'quota', '免费用户搜索数量'),
('quota.free.api_daily_limit', '100', 'integer', 'quota', '免费用户每日API调用限额'),
('quota.free.storage_limit_mb', '500', 'integer', 'quota', '免费用户存储限额(MB)')
ON CONFLICT (setting_key) DO NOTHING;

-- 9. 会员等级配额配置 - pro
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('quota.pro.article_daily_limit', '50', 'integer', 'quota', 'Pro用户每日文章限额'),
('quota.pro.article_monthly_limit', '500', 'integer', 'quota', 'Pro用户每月文章限额'),
('quota.pro.spider_num', '30', 'integer', 'quota', 'Pro用户搜索数量'),
('quota.pro.api_daily_limit', '1000', 'integer', 'quota', 'Pro用户每日API调用限额'),
('quota.pro.storage_limit_mb', '5000', 'integer', 'quota', 'Pro用户存储限额(MB)')
ON CONFLICT (setting_key) DO NOTHING;

-- 10. 会员等级配额配置 - ultra
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('quota.ultra.article_daily_limit', '200', 'integer', 'quota', 'Ultra用户每日文章限额'),
('quota.ultra.article_monthly_limit', '2000', 'integer', 'quota', 'Ultra用户每月文章限额'),
('quota.ultra.spider_num', '50', 'integer', 'quota', 'Ultra用户搜索数量'),
('quota.ultra.api_daily_limit', '10000', 'integer', 'quota', 'Ultra用户每日API调用限额'),
('quota.ultra.storage_limit_mb', '50000', 'integer', 'quota', 'Ultra用户存储限额(MB)')
ON CONFLICT (setting_key) DO NOTHING;

-- 11. 设置管理员为 ultra 等级
UPDATE users SET membership_tier = 'ultra' WHERE is_superuser = TRUE AND membership_tier = 'free';
