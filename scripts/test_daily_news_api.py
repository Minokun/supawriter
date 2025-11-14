#!/usr/bin/env python3
"""
测试每日新闻API接口
验证机器之心和站长之家API是否正常工作
"""

import requests
import json
from datetime import datetime

def test_jiqizhixin_api():
    """测试机器之心API"""
    print("=" * 60)
    print("🤖 测试机器之心API")
    print("=" * 60)
    
    try:
        url = "https://www.jiqizhixin.com/api/article_library/articles.json?sort=time&page=1&per=5"
        response = requests.get(url, timeout=30)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            print(f"✅ 获取到 {len(articles)} 篇文章")
            
            if articles:
                article = articles[0]
                print(f"✅ 第一篇文章:")
                print(f"   标题: {article.get('title', '无')[:50]}...")
                print(f"   发布时间: {article.get('publishedAt', '无')}")
                print(f"   图片: {'有' if article.get('coverImageUrl') else '无'}")
                print(f"   摘要: {'有' if article.get('content') else '无'}")
            
            return True
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_chinaz_api():
    """测试站长之家API"""
    print("\n" + "=" * 60)
    print("📰 测试站长之家实时新闻API")
    print("=" * 60)
    
    try:
        url = "https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type=1&page=1&pagesize=5"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://app.chinaz.com/',
            'Accept': 'application/json, text/plain, */*',
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                news_list = data
            else:
                news_list = data.get('data', [])
            
            print(f"✅ 获取到 {len(news_list)} 条新闻")
            
            if news_list:
                news = news_list[0]
                print(f"✅ 第一条新闻:")
                print(f"   标题: {news.get('title', '无')[:50]}...")
                print(f"   发布时间: {news.get('addtime', '无')}")
                print(f"   图片: {'有' if news.get('thumb') else '无'}")
                print(f"   描述: {'有' if news.get('description') else '无'}")
            
            return True
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    """主函数"""
    print("🔍 每日新闻API测试工具")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试API
    jiqizhixin_ok = test_jiqizhixin_api()
    chinaz_ok = test_chinaz_api()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"机器之心API: {'✅ 正常' if jiqizhixin_ok else '❌ 异常'}")
    print(f"站长之家API: {'✅ 正常' if chinaz_ok else '❌ 异常'}")
    
    if jiqizhixin_ok and chinaz_ok:
        print("\n🎉 所有API测试通过，可以正常生成每日新闻！")
        return 0
    else:
        print("\n⚠️  部分API测试失败，请检查网络连接或API状态")
        return 1

if __name__ == "__main__":
    exit(main())
