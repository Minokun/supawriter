#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 0 环境验证脚本"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def verify_dependencies():
    """验证依赖安装"""
    print("=" * 60)
    print("1. 验证 Python 依赖")
    print("=" * 60)
    
    required_packages = ['redis', 'cryptography', 'pytest_asyncio']
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")
            return False
    return True

def verify_config():
    """验证配置文件"""
    print("\n" + "=" * 60)
    print("2. 验证配置文件")
    print("=" * 60)
    
    try:
        from backend.api.config import settings
        print(f"✅ 配置加载成功")
        print(f"   - REDIS_HOST: {settings.REDIS_HOST}")
        print(f"   - REDIS_PORT: {settings.REDIS_PORT}")
        print(f"   - REDIS_DB: {settings.REDIS_DB}")
        print(f"   - REDIS_URL: {settings.REDIS_URL}")
        print(f"   - ENCRYPTION_KEY: {'已配置' if settings.ENCRYPTION_KEY else '未配置（将使用临时密钥）'}")
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

def verify_encryption():
    """验证加密工具"""
    print("\n" + "=" * 60)
    print("3. 验证加密工具")
    print("=" * 60)
    
    try:
        from backend.api.core.encryption import encryption_manager
        
        # 测试加密解密
        test_text = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"
        encrypted = encryption_manager.encrypt(test_text)
        decrypted = encryption_manager.decrypt(encrypted)
        preview = encryption_manager.generate_preview(test_text)
        
        assert decrypted == test_text, "加密解密不匹配"
        
        print(f"✅ 加密工具正常")
        print(f"   - 原文: {test_text[:20]}...")
        print(f"   - 密文: {encrypted[:40]}...")
        print(f"   - 预览: {preview}")
        return True
    except Exception as e:
        print(f"❌ 加密工具测试失败: {e}")
        return False

def verify_redis():
    """验证 Redis 连接"""
    print("\n" + "=" * 60)
    print("4. 验证 Redis 连接")
    print("=" * 60)
    
    try:
        from backend.api.core.redis_client import redis_client
        
        # 测试同步连接
        result = redis_client.ping()
        if result:
            print(f"✅ Redis 连接成功")
            
            # 测试基本操作
            redis_client.sync_client.set("test_key", "test_value", ex=10)
            value = redis_client.sync_client.get("test_key")
            assert value == "test_value", "Redis 读写测试失败"
            print(f"✅ Redis 读写测试通过")
            return True
        else:
            print(f"⚠️  Redis 连接失败（这不会阻止开发，但某些功能需要 Redis）")
            print(f"   提示: 运行 'brew services start redis' 启动 Redis")
            return False
    except Exception as e:
        print(f"⚠️  Redis 测试失败: {e}")
        print(f"   提示: Redis 是可选的，可以稍后配置")
        return False

def verify_database():
    """验证数据库连接"""
    print("\n" + "=" * 60)
    print("5. 验证数据库连接")
    print("=" * 60)
    
    try:
        from utils.database import Database
        
        with Database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT version()')
            version = cursor.fetchone()[0]
            print(f"✅ 数据库连接成功")
            print(f"   - PostgreSQL 版本: {version.split(',')[0]}")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "🚀 " * 20)
    print("Phase 0 环境验证")
    print("🚀 " * 20 + "\n")
    
    results = {
        "依赖安装": verify_dependencies(),
        "配置文件": verify_config(),
        "加密工具": verify_encryption(),
        "Redis连接": verify_redis(),
        "数据库连接": verify_database()
    }
    
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    # Redis 是可选的，不计入失败
    critical_checks = ["依赖安装", "配置文件", "加密工具", "数据库连接"]
    critical_results = [results[k] for k in critical_checks]
    
    if all(critical_results):
        print("\n" + "🎉 " * 20)
        print("Phase 0 环境准备完成！可以进入 Phase 1")
        print("🎉 " * 20)
        return 0
    else:
        print("\n" + "⚠️  " * 20)
        print("存在失败项，请修复后再继续")
        print("⚠️  " * 20)
        return 1

if __name__ == "__main__":
    sys.exit(main())
