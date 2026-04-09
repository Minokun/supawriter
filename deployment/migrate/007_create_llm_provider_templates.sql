-- -*- coding: utf-8 -*-
-- LLM 提供商模板表
-- 用于存储系统级的 LLM 提供商配置，作为用户配置的模板

-- 创建系统级 LLM 提供商模板表
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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_llm_provider_templates_provider_id ON llm_provider_templates(provider_id);
CREATE INDEX IF NOT EXISTS idx_llm_provider_templates_category ON llm_provider_templates(category);
CREATE INDEX IF NOT EXISTS idx_llm_provider_templates_active ON llm_provider_templates(is_active);

-- 创建更新时间触发器
CREATE TRIGGER update_llm_provider_templates_updated_at
    BEFORE UPDATE ON llm_provider_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 添加表注释
COMMENT ON TABLE llm_provider_templates IS '系统级 LLM 提供商模板表，存储所有可用的提供商配置';
COMMENT ON COLUMN llm_provider_templates.provider_id IS '提供商唯一标识符 (openai, deepseek, kimi 等)';
COMMENT ON COLUMN llm_provider_templates.provider_name IS '提供商显示名称';
COMMENT ON COLUMN llm_provider_templates.display_name IS '本地化显示名称（可选）';
COMMENT ON COLUMN llm_provider_templates.base_url IS '默认 API 基础 URL';
COMMENT ON COLUMN llm_provider_templates.default_models IS '默认模型列表（JSONB 数组）';
COMMENT ON COLUMN llm_provider_templates.category IS '分类: proprietary=商业API, open_source=开源, self_hosted=自建';
COMMENT ON COLUMN llm_provider_templates.description IS '提供商描述';
COMMENT ON COLUMN llm_provider_templates.icon_url IS '图标 URL（可选）';
COMMENT ON COLUMN llm_provider_templates.official_docs_url IS '官方文档链接（可选）';
COMMENT ON COLUMN llm_provider_templates.requires_api_key IS '是否需要 API Key';
COMMENT ON COLUMN llm_provider_templates.is_active IS '是否启用（管理员可禁用）';
COMMENT ON COLUMN llm_provider_templates.version IS '版本号（用于更新追踪）';

-- 初始化 11 个提供商模板数据
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
