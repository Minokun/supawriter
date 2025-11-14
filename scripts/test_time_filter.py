#!/usr/bin/env python3
"""
测试时间筛选逻辑
验证机器之心新闻的时间筛选是否正确
"""

import requests
from datetime import datetime, timedelta

def test_time_filter():
    """测试时间筛选逻辑"""
    print("🕒 测试机器之心新闻时间筛选")
    print("=" * 60)
    
    # 获取当前时间范围
    yesterday = datetime.now() - timedelta(days=1)
    today = datetime.now()
    
    print(f"筛选范围: {yesterday.date()} 到 {today.date()}")
    print(f"当前时间: {today.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        url = "https://www.jiqizhixin.com/api/article_library/articles.json?sort=time&page=1&per=20"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            print(f"获取到 {len(articles)} 篇文章，开始筛选:")
            print("-" * 60)
            
            included_count = 0
            excluded_count = 0
            
            for i, article in enumerate(articles, 1):
                title = article.get('title', '无标题')[:50] + '...'
                published_at = article.get('publishedAt', '')
                
                if published_at:
                    try:
                        # 解析时间
                        dt = datetime.strptime(published_at, '%Y/%m/%d %H:%M')
                        
                        # 检查是否在范围内
                        if yesterday.date() <= dt.date() <= today.date():
                            print(f"{i:2d}. ✅ {title}")
                            print(f"     时间: {published_at} (在范围内)")
                            included_count += 1
                        else:
                            print(f"{i:2d}. ❌ {title}")
                            print(f"     时间: {published_at} (超出范围)")
                            excluded_count += 1
                    except Exception as e:
                        print(f"{i:2d}. ⚠️  {title}")
                        print(f"     时间: {published_at} (解析失败: {e})")
                        excluded_count += 1
                else:
                    print(f"{i:2d}. ⚠️  {title}")
                    print(f"     时间: 无 (缺少时间信息)")
                    excluded_count += 1
                
                print()
            
            print("=" * 60)
            print("📊 筛选结果统计:")
            print(f"   包含文章: {included_count} 篇")
            print(f"   排除文章: {excluded_count} 篇")
            print(f"   总计文章: {len(articles)} 篇")
            print(f"   筛选率: {included_count/len(articles)*100:.1f}%")
            
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_time_filter()
