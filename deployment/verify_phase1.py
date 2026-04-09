#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 1 系统设置模块验证脚本"""

import sys
import os
import requests
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("=" * 60)
    print("1. 测试健康检查")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过")
            print(f"   - 服务: {data.get('service')}")
            print(f"   - 版本: {data.get('version')}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_database_tables():
    """测试数据库表是否创建成功"""
    print("\n" + "=" * 60)
    print("2. 测试数据库表")
    print("=" * 60)
    
    try:
        from utils.database import Database
        
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name IN ('user_api_keys', 'user_model_configs', 'user_preferences')
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            
            expected_tables = {'user_api_keys', 'user_model_configs', 'user_preferences'}
            found_tables = {row['table_name'] for row in tables}
            
            if expected_tables == found_tables:
                print(f"✅ 所有表已创建")
                for table in sorted(found_tables):
                    print(f"   - {table}")
                return True
            else:
                missing = expected_tables - found_tables
                print(f"❌ 缺少表: {missing}")
                return False
    except Exception as e:
        print(f"❌ 数据库表检查失败: {e}")
        return False

def test_api_endpoints():
    """测试 API 端点"""
    print("\n" + "=" * 60)
    print("3. 测试 API 端点")
    print("=" * 60)
    
    # 注意：这些测试需要有效的 JWT token
    # 这里只测试端点是否存在
    
    endpoints = [
        "/api/v1/settings/keys",
        "/api/v1/settings/models",
        "/api/v1/settings/preferences"
    ]
    
    all_ok = True
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            # 401 表示需要认证，说明端点存在
            if response.status_code in [200, 401]:
                print(f"✅ {endpoint} - 端点存在")
            else:
                print(f"⚠️  {endpoint} - 状态码: {response.status_code}")
                all_ok = False
        except Exception as e:
            print(f"❌ {endpoint} - 失败: {e}")
            all_ok = False
    
    return all_ok

def test_encryption():
    """测试加密功能"""
    print("\n" + "=" * 60)
    print("4. 测试加密功能")
    print("=" * 60)
    
    try:
        from backend.api.core.encryption import encryption_manager
        
        # 测试加密解密
        test_keys = [
            "sk-test1234567890",
            "deepseek-api-key-12345",
            "qwen-key-abcdefg"
        ]
        
        for key in test_keys:
            encrypted = encryption_manager.encrypt(key)
            decrypted = encryption_manager.decrypt(encrypted)
            preview = encryption_manager.generate_preview(key)
            
            if decrypted == key:
                print(f"✅ 加密测试通过: {preview}")
            else:
                print(f"❌ 加密测试失败: {key}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ 加密功能测试失败: {e}")
        return False

def test_redis_client():
    """测试 Redis 客户端"""
    print("\n" + "=" * 60)
    print("5. 测试 Redis 客户端")
    print("=" * 60)
    
    try:
        from backend.api.core.redis_client import redis_client
        
        # 测试连接
        if redis_client.ping():
            print(f"✅ Redis 连接正常")
            
            # 测试基本操作
            test_key = "test:phase1:verification"
            test_value = "phase1_ok"
            
            redis_client.sync_client.set(test_key, test_value, ex=10)
            retrieved = redis_client.sync_client.get(test_key)
            
            if retrieved == test_value:
                print(f"✅ Redis 读写测试通过")
                redis_client.sync_client.delete(test_key)
                return True
            else:
                print(f"❌ Redis 读写测试失败")
                return False
        else:
            print(f"⚠️  Redis 连接失败（可选功能）")
            return False
    except Exception as e:
        print(f"⚠️  Redis 测试失败: {e}（可选功能）")
        return False

def test_api_docs():
    """测试 API 文档"""
    print("\n" + "=" * 60)
    print("6. 测试 API 文档")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print(f"✅ API 文档可访问: {BASE_URL}/docs")
            return True
        else:
            print(f"❌ API 文档不可访问")
            return False
    except Exception as e:
        print(f"❌ API 文档测试失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "🚀 " * 20)
    print("Phase 1 系统设置模块验证")
    print("🚀 " * 20 + "\n")
    
    results = {
        "健康检查": test_health(),
        "数据库表": test_database_tables(),
        "API端点": test_api_endpoints(),
        "加密功能": test_encryption(),
        "Redis客户端": test_redis_client(),
        "API文档": test_api_docs()
    }
    
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    # Redis 是可选的
    critical_checks = ["健康检查", "数据库表", "API端点", "加密功能", "API文档"]
    critical_results = [results[k] for k in critical_checks]
    
    if all(critical_results):
        print("\n" + "🎉 " * 20)
        print("Phase 1 系统设置模块开发完成！")
        print("可以访问 http://localhost:8000/docs 查看 API 文档")
        print("🎉 " * 20)
        return 0
    else:
        print("\n" + "⚠️  " * 20)
        print("存在失败项，请检查后再继续")
        print("⚠️  " * 20)
        return 1

if __name__ == "__main__":
    sys.exit(main())
