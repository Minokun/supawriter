-- 创建用户设置相关表

-- 1. 用户 API 密钥表
CREATE TABLE IF NOT EXISTS user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    key_preview VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider)
);

CREATE INDEX idx_user_api_keys_user_id ON user_api_keys(user_id);
CREATE INDEX idx_user_api_keys_provider ON user_api_keys(provider);

-- 2. 用户模型配置表
CREATE TABLE IF NOT EXISTS user_model_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    chat_model VARCHAR(100) DEFAULT 'openai:gpt-4',
    writer_model VARCHAR(100) DEFAULT 'deepseek:deepseek-chat',
    embedding_model VARCHAR(100) DEFAULT 'openai:text-embedding-3-small',
    image_model VARCHAR(100) DEFAULT 'openai:dall-e-3',
    default_temperature DECIMAL(3,2) DEFAULT 0.7,
    default_max_tokens INTEGER DEFAULT 4096,
    default_top_p DECIMAL(3,2) DEFAULT 1.0,
    enable_streaming BOOLEAN DEFAULT TRUE,
    enable_thinking_process BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_model_configs_user_id ON user_model_configs(user_id);

-- 3. 用户偏好设置表
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    editor_font_size INTEGER DEFAULT 14,
    editor_theme VARCHAR(20) DEFAULT 'light',
    auto_save_interval INTEGER DEFAULT 30,
    default_article_style VARCHAR(50) DEFAULT 'professional',
    default_article_length VARCHAR(20) DEFAULT 'medium',
    default_language VARCHAR(10) DEFAULT 'zh-CN',
    sidebar_collapsed BOOLEAN DEFAULT FALSE,
    theme_mode VARCHAR(20) DEFAULT 'light',
    email_notifications BOOLEAN DEFAULT TRUE,
    task_complete_notification BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- 4. LLM 提供商配置表（全局或用户级别）
CREATE TABLE IF NOT EXISTS llm_providers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_id VARCHAR(50) NOT NULL,
    provider_name VARCHAR(100) NOT NULL,
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,
    models JSONB DEFAULT '[]',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider_id)
);

CREATE INDEX idx_llm_providers_user_id ON llm_providers(user_id);
CREATE INDEX idx_llm_providers_provider_id ON llm_providers(provider_id);

-- 5. 其他服务配置表（七牛云、SERPER 等）
CREATE TABLE IF NOT EXISTS user_service_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    qiniu_domain VARCHAR(255),
    qiniu_folder VARCHAR(255),
    qiniu_access_key_encrypted TEXT,
    qiniu_secret_key_encrypted TEXT,
    qiniu_region VARCHAR(10),
    serper_api_key_encrypted TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_service_configs_user_id ON user_service_configs(user_id);

-- 添加注释
COMMENT ON TABLE user_api_keys IS '用户 API 密钥存储表';
COMMENT ON TABLE user_model_configs IS '用户模型配置表';
COMMENT ON TABLE user_preferences IS '用户偏好设置表';
COMMENT ON TABLE llm_providers IS 'LLM 提供商配置表';
COMMENT ON TABLE user_service_configs IS '用户其他服务配置表（七牛云、SERPER等）';
