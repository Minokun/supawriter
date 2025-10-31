#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 DDGS + Serper 双引擎搜索功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def main():
    """测试 DDGS + Serper 搜索"""
    from utils.searxng_utils import Search
    from settings import DEFAULT_SPIDER_NUM
    
    print("=" * 70)
    print("  测试 DDGS + Serper 双引擎搜索")
    print("=" * 70)
    
    # 初始化搜索
    searcher = Search(result_num=DEFAULT_SPIDER_NUM)
    query = "2025 docker swarm的完整教程"
    
    print(f"\n🔍 测试查询: {query}")
    print(f"📊 DDGS 结果数限制: {DEFAULT_SPIDER_NUM}")
    print(f"📊 Serper 结果数: ~10 (API 固定返回)")
    print(f"📊 预期总结果数: 约 {DEFAULT_SPIDER_NUM + 10} 条\n")
    
    try:
        # 执行搜索
        results = searcher.query_search(query)
        
        if results and 'results' in results:
            result_list = results['results']
            print(f"✅ 搜索成功! 返回 {len(result_list)} 条结果\n")
            
            # 统计来源
            ddgs_count = sum(1 for r in result_list if r.get('source') == 'ddgs')
            serper_count = sum(1 for r in result_list if r.get('source') == 'serper')
            
            print(f"📊 结果来源统计:")
            print(f"   DDGS:   {ddgs_count} 条")
            print(f"   Serper: {serper_count} 条")
            print(f"   总计:   {len(result_list)} 条\n")
            
            # 显示前5条结果
            print("=" * 70)
            print("前 5 条搜索结果：")
            print("=" * 70)
            for idx, item in enumerate(result_list[:5], 1):
                print(f"\n【结果 #{idx}】 来源: {item.get('source', 'unknown')}")
                print(f"  标题: {item.get('title', 'N/A')}")
                print(f"  URL: {item.get('url', 'N/A')}")
                print(f"  内容: {item.get('content', 'N/A')[:150]}...")
                print(f"  分数: {item.get('score', 0):.3f}")
        else:
            print("❌ 搜索失败，未返回结果")
            
    except Exception as e:
        logger.error(f"搜索过程中发生错误: {e}", exc_info=True)
        print(f"\n❌ 错误: {e}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
