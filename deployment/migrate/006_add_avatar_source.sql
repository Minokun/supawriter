-- =============================================================================
-- Migration: Add avatar_source field to users table
-- =============================================================================
-- Purpose: Track where user avatars come from to implement proper priority logic
-- Created: 2026-02-10
-- =============================================================================

-- Add avatar_source column to track avatar origin
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_source VARCHAR(20);

-- Valid values: 'google', 'wechat', 'manual', null (default/none)
-- Add check constraint for valid values
ALTER TABLE users ADD CONSTRAINT check_avatar_source
    CHECK (avatar_source IN ('google', 'wechat', 'manual', NULL) OR avatar_source IS NULL);

-- Update existing records:
-- 1. If user has avatar_url but no avatar_source, try to infer from oauth_accounts
-- 2. For users with Google OAuth, set avatar_source to 'google'
UPDATE users u
SET avatar_source = 'google'
WHERE u.avatar_url IS NOT NULL
  AND u.avatar_source IS NULL
  AND EXISTS (
    SELECT 1 FROM oauth_accounts oa
    WHERE oa.user_id = u.id
    AND oa.provider = 'google'
    AND oa.extra_data->>'picture' IS NOT NULL
  );

-- 3. For users with avatar_url but no OAuth match, assume 'manual'
UPDATE users
SET avatar_source = 'manual'
WHERE avatar_url IS NOT NULL
  AND avatar_source IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN users.avatar_source IS 'Avatar source: google, wechat, manual, or NULL';
