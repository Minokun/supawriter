#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serper 搜索 API 简单测试脚本
测试查询："2025 docker swarm的完整教程"
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.serper_search import serper_search
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    # 从环境变量或 Streamlit secrets 获取 API Key
    api_key = os.environ.get('SERPER_API_KEY')
    
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get('SERPER_API_KEY')
        except:
            pass
    
    if not api_key:
        print("❌ 未找到 Serper API Key")
        print("\n请设置环境变量: export SERPER_API_KEY='your_api_key'")
        print("或在 .streamlit/secrets.toml 中配置")
        sys.exit(1)
    
    print(f"✅ 已获取 API Key: {api_key[:10]}...{api_key[-4:]}\n")
    
    # 测试查询
    query = "2025 docker swarm的完整教程"
    print(f"🔍 搜索关键词: {query}")
    print("=" * 70)
    
    # 执行搜索（Serper API 固定返回约 10 条）
    results = serper_search(api_key, query)
    
    if results:
        print(f"\n✅ 搜索成功! 返回 {len(results)} 条结果\n")
        
        # 打印所有结果
        for idx, item in enumerate(results, 1):
            print(f"【结果 #{idx}】")
            print(f"  标题: {item.get('title', 'N/A')}")
            print(f"  URL: {item.get('url', 'N/A')}")
            print(f"  内容: {item.get('content', 'N/A')[:200]}...")
            print(f"  分数: {item.get('score', 0):.3f}")
            print(f"  来源: {item.get('source', 'N/A')}")
            print()
    else:
        print("\n❌ 搜索失败，未返回结果")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
