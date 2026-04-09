-- 统一登录机制优化 — 数据库迁移
-- 新增 phone/email_verified/phone_verified 字段，以及 oauth_accounts 唯一约束

-- users 表新增字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- oauth_accounts 表新增唯一约束（防止重复绑定）
-- 同一 provider 的同一 provider_user_id 只能绑定一次
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_provider_user'
  ) THEN
    ALTER TABLE oauth_accounts ADD CONSTRAINT uq_provider_user 
      UNIQUE (provider, provider_user_id);
  END IF;
END $$;

-- 同一用户只能绑定同一 provider 一次
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_user_provider'
  ) THEN
    ALTER TABLE oauth_accounts ADD CONSTRAINT uq_user_provider 
      UNIQUE (user_id, provider);
  END IF;
END $$;
