#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SupaWriter 完整验证脚本
验证所有 Phase 0-3 的功能
"""

import sys
import os
import requests
import json
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = "http://localhost:8000"

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_phase0():
    """Phase 0: 环境准备验证"""
    print_section("Phase 0: 环境准备")
    
    results = {}
    
    # 1. Python 依赖
    print("\n📦 检查 Python 依赖...")
    required_packages = ['redis', 'cryptography', 'pytest_asyncio', 'fastapi', 'uvicorn']
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
            results[f"dep_{package}"] = True
        except ImportError:
            print(f"  ❌ {package}")
            results[f"dep_{package}"] = False
    
    # 2. Redis 连接
    print("\n🔴 检查 Redis 连接...")
    try:
        from backend.api.core.redis_client import redis_client
        if redis_client.ping():
            print(f"  ✅ Redis 连接正常")
            results['redis'] = True
        else:
            print(f"  ❌ Redis 连接失败")
            results['redis'] = False
    except Exception as e:
        print(f"  ❌ Redis 测试失败: {e}")
        results['redis'] = False
    
    # 3. 加密工具
    print("\n🔐 检查加密工具...")
    try:
        from backend.api.core.encryption import encryption_manager
        test_text = "test_api_key_123"
        encrypted = encryption_manager.encrypt(test_text)
        decrypted = encryption_manager.decrypt(encrypted)
        if decrypted == test_text:
            print(f"  ✅ 加密解密正常")
            results['encryption'] = True
        else:
            print(f"  ❌ 加密解密失败")
            results['encryption'] = False
    except Exception as e:
        print(f"  ❌ 加密工具测试失败: {e}")
        results['encryption'] = False
    
    # 4. 数据库连接
    print("\n🗄️  检查数据库连接...")
    try:
        from utils.database import Database
        with Database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT version()')
            version = cursor.fetchone()[0]
            print(f"  ✅ 数据库连接正常")
            print(f"     版本: {version.split(',')[0]}")
            results['database'] = True
    except Exception as e:
        print(f"  ❌ 数据库连接失败: {e}")
        results['database'] = False
    
    return results

def test_phase1():
    """Phase 1: 系统设置模块验证"""
    print_section("Phase 1: 系统设置模块")
    
    results = {}
    
    # 1. 数据库表
    print("\n📊 检查数据库表...")
    try:
        from utils.database import Database
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name IN ('user_api_keys', 'user_model_configs', 'user_preferences')
                ORDER BY table_name
            """)
            tables = [row['table_name'] for row in cursor.fetchall()]
            
            expected = ['user_api_keys', 'user_model_configs', 'user_preferences']
            for table in expected:
                if table in tables:
                    print(f"  ✅ {table}")
                    results[f"table_{table}"] = True
                else:
                    print(f"  ❌ {table} 不存在")
                    results[f"table_{table}"] = False
    except Exception as e:
        print(f"  ❌ 数据库表检查失败: {e}")
        results['tables'] = False
    
    # 2. API 端点
    print("\n🌐 检查 API 端点...")
    endpoints = [
        ('GET', '/api/v1/settings/keys'),
        ('GET', '/api/v1/settings/models'),
        ('GET', '/api/v1/settings/preferences'),
    ]
    
    for method, endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            # 401 表示需要认证，说明端点存在
            if response.status_code in [200, 401]:
                print(f"  ✅ {method} {endpoint}")
                results[f"api_{endpoint}"] = True
            else:
                print(f"  ⚠️  {method} {endpoint} - 状态码: {response.status_code}")
                results[f"api_{endpoint}"] = False
        except Exception as e:
            print(f"  ❌ {method} {endpoint} - 失败: {e}")
            results[f"api_{endpoint}"] = False
    
    return results

def test_phase2():
    """Phase 2: 文章生成增强验证"""
    print_section("Phase 2: 文章生成增强")
    
    results = {}
    
    # 1. 服务模块
    print("\n🤖 检查文章生成服务...")
    try:
        from backend.api.services.article_generator import article_generator
        print(f"  ✅ 文章生成服务已加载")
        results['article_service'] = True
    except Exception as e:
        print(f"  ❌ 文章生成服务加载失败: {e}")
        results['article_service'] = False
    
    # 2. Utils 模块复用
    print("\n📚 检查 utils 模块复用...")
    modules = {
        'searxng_utils': 'utils.searxng_utils',
        'article_queue': 'utils.article_queue',
        'llm_chat': 'utils.llm_chat',
        'prompt_template': 'utils.prompt_template',
        'wechat_converter': 'utils.wechat_converter'
    }
    
    for name, module_path in modules.items():
        try:
            __import__(module_path)
            print(f"  ✅ {name}")
            results[f"utils_{name}"] = True
        except Exception as e:
            print(f"  ❌ {name} - {e}")
            results[f"utils_{name}"] = False
    
    # 3. Redis 队列功能
    print("\n📋 检查 Redis 队列功能...")
    try:
        from backend.api.core.redis_client import redis_client
        
        async def test_queue():
            test_user_id = 99999
            test_article_id = "verify_test_123"
            
            # 添加到队列
            await redis_client.add_to_user_queue(test_user_id, test_article_id)
            
            # 获取队列
            queue = await redis_client.get_user_queue(test_user_id, 10)
            
            # 设置进度
            await redis_client.set_article_progress(test_article_id, {
                "status": "running",
                "progress_percent": 50
            })
            
            # 获取进度
            progress = await redis_client.get_article_progress(test_article_id)
            
            # 清理
            await redis_client.remove_from_queue(test_user_id, test_article_id)
            await redis_client.delete_article_progress(test_article_id)
            
            return len(queue) > 0 and progress is not None
        
        if asyncio.run(test_queue()):
            print(f"  ✅ Redis 队列功能正常")
            results['redis_queue'] = True
        else:
            print(f"  ❌ Redis 队列功能异常")
            results['redis_queue'] = False
    except Exception as e:
        print(f"  ❌ Redis 队列测试失败: {e}")
        results['redis_queue'] = False
    
    # 4. API 端点
    print("\n🌐 检查文章生成 API...")
    endpoints = [
        ('POST', '/api/v1/articles/generate/stream'),
        ('GET', '/api/v1/articles/queue'),
    ]
    
    for method, endpoint in endpoints:
        try:
            if method == 'POST':
                response = requests.post(
                    f"{BASE_URL}{endpoint}",
                    json={"topic": "test"},
                    timeout=5
                )
            else:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            
            if response.status_code in [200, 401, 422]:
                print(f"  ✅ {method} {endpoint}")
                results[f"api_{endpoint}"] = True
            else:
                print(f"  ⚠️  {method} {endpoint} - 状态码: {response.status_code}")
                results[f"api_{endpoint}"] = False
        except Exception as e:
            print(f"  ❌ {method} {endpoint} - 失败: {e}")
            results[f"api_{endpoint}"] = False
    
    return results

def test_phase3():
    """Phase 3: 热点与历史验证"""
    print_section("Phase 3: 热点与历史")
    
    results = {}
    
    # 1. 热点服务
    print("\n🔥 检查热点服务...")
    try:
        from backend.api.services.hotspots_service import hotspots_service
        print(f"  ✅ 热点服务已加载")
        results['hotspots_service'] = True
    except Exception as e:
        print(f"  ❌ 热点服务加载失败: {e}")
        results['hotspots_service'] = False
    
    # 2. 热点 API
    print("\n🌐 检查热点 API...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/hotspots/sources", timeout=5)
        if response.status_code == 200:
            data = response.json()
            sources = data.get('sources', [])
            print(f"  ✅ 热点源列表 API - 找到 {len(sources)} 个源")
            for source in sources:
                print(f"     {source['icon']} {source['name']}")
            results['hotspots_api'] = True
        else:
            print(f"  ❌ 热点源列表 API - 状态码: {response.status_code}")
            results['hotspots_api'] = False
    except Exception as e:
        print(f"  ❌ 热点 API 测试失败: {e}")
        results['hotspots_api'] = False
    
    # 3. Redis 缓存
    print("\n💾 检查 Redis 缓存功能...")
    try:
        from backend.api.core.redis_client import redis_client
        
        async def test_cache():
            test_source = "test_source"
            test_data = [{"title": "测试", "url": "http://test.com"}]
            
            # 设置缓存
            await redis_client.cache_hotspots(test_source, test_data, 60)
            
            # 获取缓存
            cached = await redis_client.get_cached_hotspots(test_source)
            
            # 清理
            await redis_client.async_client.delete(f"hotspots:{test_source}")
            
            return cached is not None and len(cached) > 0
        
        if asyncio.run(test_cache()):
            print(f"  ✅ Redis 缓存功能正常")
            results['redis_cache'] = True
        else:
            print(f"  ❌ Redis 缓存功能异常")
            results['redis_cache'] = False
    except Exception as e:
        print(f"  ❌ Redis 缓存测试失败: {e}")
        results['redis_cache'] = False
    
    return results

def test_docker_deployment():
    """容器化部署验证"""
    print_section("容器化部署配置")
    
    results = {}
    
    # 检查 Docker 配置文件
    print("\n🐳 检查 Docker 配置文件...")
    files = [
        'deployment/docker-compose.yml',
        'deployment/Dockerfile.backend',
        'deployment/Dockerfile.frontend',
        'deployment/Dockerfile.streamlit',
        'deployment/nginx/nginx.conf',
        'deployment/nginx/conf.d/supawriter.conf',
        'deployment/docker-start.sh',
        'deployment/README.md',
        'deployment/postgres/bootstrap/001_extensions.sql',
    ]
    
    for file_path in files:
        full_path = os.path.join('/Users/wxk/Desktop/workspace/supawriter', file_path)
        if os.path.exists(full_path):
            print(f"  ✅ {file_path}")
            results[f"file_{file_path}"] = True
        else:
            print(f"  ❌ {file_path} 不存在")
            results[f"file_{file_path}"] = False
    
    return results

def generate_report(all_results):
    """生成验证报告"""
    print_section("验证报告")
    
    phase_results = {
        'Phase 0: 环境准备': all_results['phase0'],
        'Phase 1: 系统设置': all_results['phase1'],
        'Phase 2: 文章生成': all_results['phase2'],
        'Phase 3: 热点历史': all_results['phase3'],
        '容器化部署': all_results['docker']
    }
    
    print("\n📊 各阶段通过率:")
    total_passed = 0
    total_tests = 0
    
    for phase_name, results in phase_results.items():
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        total_passed += passed
        total_tests += total
        percentage = (passed / total * 100) if total > 0 else 0
        
        status = "✅" if percentage == 100 else "⚠️" if percentage >= 80 else "❌"
        print(f"  {status} {phase_name}: {passed}/{total} ({percentage:.1f}%)")
    
    overall_percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 总体通过率: {total_passed}/{total_tests} ({overall_percentage:.1f}%)")
    
    if overall_percentage >= 90:
        print("\n" + "🎉 " * 20)
        print("验证通过！系统已准备就绪！")
        print("🎉 " * 20)
        return 0
    elif overall_percentage >= 70:
        print("\n" + "⚠️  " * 20)
        print("大部分功能正常，但存在一些问题需要修复")
        print("⚠️  " * 20)
        return 1
    else:
        print("\n" + "❌ " * 20)
        print("存在较多问题，请检查后重试")
        print("❌ " * 20)
        return 2

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("SupaWriter 完整验证")
    print("验证 Phase 0-3 所有功能")
    print("🚀 " * 30)
    
    all_results = {
        'phase0': test_phase0(),
        'phase1': test_phase1(),
        'phase2': test_phase2(),
        'phase3': test_phase3(),
        'docker': test_docker_deployment()
    }
    
    return generate_report(all_results)

if __name__ == "__main__":
    sys.exit(main())
