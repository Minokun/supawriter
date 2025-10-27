#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 CSDN 图片下载功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.embedding_utils import Embedding
import logging

logging.basicConfig(level=logging.INFO)

# 测试 CSDN 图片 URL
test_urls = [
    "https://i-blog.csdnimg.cn/blog_migrate/01743fcd47a1dfc7e55a0c507dc727bd.jpeg",
    "https://img-blog.csdnimg.cn/20210101120000123.png",  # 另一个 CSDN 图片格式
]

print("=" * 80)
print("测试 CSDN 图片下载（防盗链优化后）")
print("=" * 80)

embedding = Embedding()

for i, url in enumerate(test_urls, 1):
    print(f"\n[{i}] 测试 URL: {url}")
    try:
        result = embedding.get_embedding([url], is_image_url=True)
        if result and len(result) > 0:
            print(f"    ✅ 成功！获得嵌入向量，维度: {len(result[0]) if result[0] else 'N/A'}")
        else:
            print(f"    ⚠️  返回空结果")
    except Exception as e:
        print(f"    ❌ 失败: {e}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
