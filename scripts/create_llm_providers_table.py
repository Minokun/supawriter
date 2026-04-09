#!/usr/bin/env python3
"""
创建 llm_providers 表的迁移脚本
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import quote_plus

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_llm_providers_table():
    """创建 llm_providers 和 user_service_configs 表"""
    
    # 从环境变量读取数据库连接，优先使用 deployment/.env 中的配置
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # 尝试从 deployment/.env 读取
        deployment_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'deployment', '.env')
        if os.path.exists(deployment_env):
            with open(deployment_env, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        database_url = line.split('=', 1)[1].strip()
                        break
    
    if not database_url:
        # 使用默认配置
        host = '122.51.24.120'
        port = '5432'
        database = 'supawriter'
        user = 'supawriter'
        password = '^1234qwerasdf$'
        database_url = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
    
    print(f"连接到数据库: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    try:
        # 连接数据库
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("开始创建表...")
        
        # 创建 llm_providers 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_providers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider_id VARCHAR(50) NOT NULL,
                provider_name VARCHAR(100) NOT NULL,
                base_url TEXT NOT NULL,
                api_key_encrypted TEXT,
                models JSONB DEFAULT '[]',
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id, provider_id)
            );
        """)
        print("✓ llm_providers 表创建成功")
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_providers_user_id ON llm_providers(user_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_providers_provider_id ON llm_providers(provider_id);
        """)
        print("✓ llm_providers 索引创建成功")
        
        # 创建 user_service_configs 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_service_configs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                qiniu_domain VARCHAR(255),
                qiniu_folder VARCHAR(255),
                qiniu_access_key_encrypted TEXT,
                qiniu_secret_key_encrypted TEXT,
                qiniu_region VARCHAR(10),
                serper_api_key_encrypted TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        print("✓ user_service_configs 表创建成功")
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_service_configs_user_id ON user_service_configs(user_id);
        """)
        print("✓ user_service_configs 索引创建成功")
        
        # 添加注释
        cursor.execute("""
            COMMENT ON TABLE llm_providers IS 'LLM 提供商配置表（用户级别）';
        """)
        cursor.execute("""
            COMMENT ON TABLE user_service_configs IS '用户其他服务配置表（七牛云、SERPER等）';
        """)
        cursor.execute("""
            COMMENT ON COLUMN llm_providers.api_key_encrypted IS 'Fernet 加密后的 API 密钥';
        """)
        cursor.execute("""
            COMMENT ON COLUMN llm_providers.models IS 'JSON 数组，存储该提供商支持的模型列表';
        """)
        cursor.execute("""
            COMMENT ON COLUMN llm_providers.enabled IS '是否启用该提供商';
        """)
        print("✓ 表注释添加成功")
        
        # 验证表是否存在
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('llm_providers', 'user_service_configs');
        """)
        tables = cursor.fetchall()
        print(f"\n已创建的表: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ 数据库迁移完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = create_llm_providers_table()
    sys.exit(0 if success else 1)
