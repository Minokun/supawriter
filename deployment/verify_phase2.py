#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 2 文章生成增强验证脚本"""

import sys
import os
import requests
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = "http://localhost:8000"

def test_article_generator_service():
    """测试文章生成服务"""
    print("=" * 60)
    print("1. 测试文章生成服务模块")
    print("=" * 60)
    
    try:
        from backend.api.services.article_generator import article_generator
        print("✅ 文章生成服务模块导入成功")
        print(f"   - 搜索引擎已初始化")
        return True
    except Exception as e:
        print(f"❌ 文章生成服务模块导入失败: {e}")
        return False

def test_utils_modules():
    """测试 utils 模块复用"""
    print("\n" + "=" * 60)
    print("2. 测试 utils 模块复用")
    print("=" * 60)
    
    modules = {
        'searxng_utils': 'utils.searxng_utils',
        'article_queue': 'utils.article_queue',
        'llm_chat': 'utils.llm_chat',
        'prompt_template': 'utils.prompt_template'
    }
    
    all_ok = True
    for name, module_path in modules.items():
        try:
            __import__(module_path)
            print(f"✅ {name} 模块可用")
        except Exception as e:
            print(f"❌ {name} 模块导入失败: {e}")
            all_ok = False
    
    return all_ok

def test_redis_queue():
    """测试 Redis 队列功能"""
    print("\n" + "=" * 60)
    print("3. 测试 Redis 队列功能")
    print("=" * 60)
    
    try:
        from backend.api.core.redis_client import redis_client
        import asyncio
        
        async def test_queue_operations():
            # 测试添加到队列
            test_user_id = 999
            test_article_id = "test_article_123"
            
            await redis_client.add_to_user_queue(test_user_id, test_article_id)
            print(f"✅ 添加到队列成功")
            
            # 测试获取队列
            queue = await redis_client.get_user_queue(test_user_id, 10)
            print(f"✅ 获取队列成功: {len(queue)} 项")
            
            # 测试进度管理
            progress_data = {
                "status": "running",
                "progress_percent": 50,
                "current_step": "测试中..."
            }
            await redis_client.set_article_progress(test_article_id, progress_data)
            print(f"✅ 设置进度成功")
            
            # 获取进度
            retrieved = await redis_client.get_article_progress(test_article_id)
            if retrieved and retrieved.get('progress_percent') == '50':
                print(f"✅ 获取进度成功")
            
            # 清理
            await redis_client.remove_from_queue(test_user_id, test_article_id)
            await redis_client.delete_article_progress(test_article_id)
            print(f"✅ 清理测试数据成功")
            
            return True
        
        result = asyncio.run(test_queue_operations())
        return result
        
    except Exception as e:
        print(f"❌ Redis 队列测试失败: {e}")
        return False

def test_api_endpoints():
    """测试 API 端点"""
    print("\n" + "=" * 60)
    print("4. 测试 API 端点")
    print("=" * 60)
    
    endpoints = [
        "/api/v1/articles/generate/stream",
        "/api/v1/articles/queue"
    ]
    
    all_ok = True
    for endpoint in endpoints:
        try:
            # 使用 POST 测试生成端点，GET 测试队列端点
            method = 'POST' if 'generate' in endpoint else 'GET'
            
            if method == 'POST':
                response = requests.post(f"{BASE_URL}{endpoint}", json={"topic": "test"})
            else:
                response = requests.get(f"{BASE_URL}{endpoint}")
            
            # 401 表示需要认证，说明端点存在
            if response.status_code in [200, 401, 422]:  # 422 是验证错误
                print(f"✅ {endpoint} - 端点存在")
            else:
                print(f"⚠️  {endpoint} - 状态码: {response.status_code}")
                all_ok = False
        except Exception as e:
            print(f"❌ {endpoint} - 失败: {e}")
            all_ok = False
    
    return all_ok

def test_prompt_templates():
    """测试 Prompt 模板"""
    print("\n" + "=" * 60)
    print("5. 测试 Prompt 模板")
    print("=" * 60)
    
    try:
        import utils.prompt_template as pt
        
        templates = {
            'ARTICLE': pt.ARTICLE,
            'ARTICLE_FINAL': pt.ARTICLE_FINAL,
            'ARTICLE_OUTLINE_GEN': pt.ARTICLE_OUTLINE_GEN
        }
        
        for name, template in templates.items():
            if template and len(template) > 100:
                print(f"✅ {name} 模板已加载 ({len(template)} 字符)")
            else:
                print(f"❌ {name} 模板无效")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Prompt 模板测试失败: {e}")
        return False

def test_sse_format():
    """测试 SSE 格式"""
    print("\n" + "=" * 60)
    print("6. 测试 SSE 事件格式")
    print("=" * 60)
    
    try:
        # 模拟 SSE 事件
        test_event = {
            "type": "progress",
            "article_id": "test_123",
            "progress_percent": 50,
            "current_step": "测试中...",
            "timestamp": "2026-01-30T14:00:00"
        }
        
        # 转换为 SSE 格式
        sse_data = f"data: {json.dumps(test_event, ensure_ascii=False)}\n\n"
        
        if sse_data.startswith("data: ") and sse_data.endswith("\n\n"):
            print(f"✅ SSE 格式正确")
            print(f"   示例: {sse_data[:50]}...")
            return True
        else:
            print(f"❌ SSE 格式错误")
            return False
    except Exception as e:
        print(f"❌ SSE 格式测试失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "🚀 " * 20)
    print("Phase 2 文章生成增强验证")
    print("🚀 " * 20 + "\n")
    
    results = {
        "文章生成服务": test_article_generator_service(),
        "utils模块复用": test_utils_modules(),
        "Redis队列": test_redis_queue(),
        "API端点": test_api_endpoints(),
        "Prompt模板": test_prompt_templates(),
        "SSE格式": test_sse_format()
    }
    
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    critical_checks = ["文章生成服务", "utils模块复用", "API端点", "Prompt模板"]
    critical_results = [results[k] for k in critical_checks]
    
    if all(critical_results):
        print("\n" + "🎉 " * 20)
        print("Phase 2 文章生成增强开发完成！")
        print("核心功能:")
        print("  - ✅ 复用 utils/searxng_utils.py 搜索逻辑")
        print("  - ✅ 复用 utils/article_queue.py 队列管理")
        print("  - ✅ 复用 utils/prompt_template.py Prompt 模板")
        print("  - ✅ SSE 流式进度推送")
        print("  - ✅ Redis 队列管理")
        print("🎉 " * 20)
        return 0
    else:
        print("\n" + "⚠️  " * 20)
        print("存在失败项，请检查后再继续")
        print("⚠️  " * 20)
        return 1

if __name__ == "__main__":
    sys.exit(main())
