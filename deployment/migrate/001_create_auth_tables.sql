-- SupaWriter 认证系统数据库Schema
-- 创建用户表和OAuth账号绑定表

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),  -- 邮箱登录的密码哈希，OAuth用户可为空
    display_name VARCHAR(100),   -- 显示名称
    avatar_url TEXT,             -- 头像URL
    motto VARCHAR(200) DEFAULT '创作改变世界',  -- 座右铭
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    
    -- 注意：至少要有密码或OAuth账号的约束在应用层验证
    -- PostgreSQL不允许在CHECK约束中使用子查询
);

-- 创建OAuth账号绑定表
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- google, wechat等
    provider_user_id VARCHAR(255) NOT NULL,  -- OAuth提供商的用户ID
    access_token TEXT,              -- 访问令牌
    refresh_token TEXT,             -- 刷新令牌
    token_expires_at TIMESTAMP,     -- 令牌过期时间
    extra_data JSONB,               -- 存储额外的用户信息（如昵称、头像等）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 同一个OAuth账号只能绑定到一个用户
    UNIQUE(provider, provider_user_id)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_oauth_user_id ON oauth_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_provider ON oauth_accounts(provider, provider_user_id);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为users表创建更新时间触发器
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为oauth_accounts表创建更新时间触发器
DROP TRIGGER IF EXISTS update_oauth_accounts_updated_at ON oauth_accounts;
CREATE TRIGGER update_oauth_accounts_updated_at 
    BEFORE UPDATE ON oauth_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入默认管理员账号（密码为: admin123）
-- 密码哈希使用SHA256: 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
INSERT INTO users (username, email, password_hash, display_name, is_superuser)
VALUES ('admin', 'admin@supawriter.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', '管理员', TRUE)
ON CONFLICT (username) DO NOTHING;

-- 创建视图：用户完整信息（包含OAuth绑定）
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

COMMENT ON TABLE users IS '用户表：存储系统用户的基本信息';
COMMENT ON TABLE oauth_accounts IS 'OAuth账号绑定表：存储用户与第三方OAuth账号的绑定关系';
COMMENT ON COLUMN users.username IS '用户名，系统内唯一标识';
COMMENT ON COLUMN users.email IS '用户邮箱，可用于登录和找回密码';
COMMENT ON COLUMN users.password_hash IS '密码哈希，使用SHA256加密';
COMMENT ON COLUMN oauth_accounts.provider IS 'OAuth提供商：google, wechat等';
COMMENT ON COLUMN oauth_accounts.provider_user_id IS 'OAuth提供商的用户唯一标识';
