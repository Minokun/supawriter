-- 用户主题表：用于保存用户自定义的研究主题
CREATE TABLE IF NOT EXISTS user_topics (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  topic_name VARCHAR(200) NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, topic_name)
);

-- 为用户ID和主题名称创建索引，提高查询性能
CREATE INDEX IF NOT EXISTS idx_user_topics_user_id ON user_topics(user_id);
CREATE INDEX IF NOT EXISTS idx_user_topics_created_at ON user_topics(created_at DESC);

-- 为更新时间创建触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_user_topics_updated_at ON user_topics;
CREATE TRIGGER update_user_topics_updated_at
  BEFORE UPDATE ON user_topics
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
