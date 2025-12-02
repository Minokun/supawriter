#!/usr/bin/env python3
"""验证新闻资讯页面的API数据解析修复"""

import requests
import json

def test_jiqizhixin():
    """测试机器之心API"""
    print("=" * 80)
    print("测试机器之心API")
    print("=" * 80)
    try:
        url = "https://www.jiqizhixin.com/api/article_library/articles.json?sort=time&page=1&per=12"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        # 使用修复后的解析逻辑
        articles = data.get('articles', [])
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 获取到 {len(articles)} 篇文章")
        
        if articles:
            article = articles[0]
            print(f"✅ 第一篇文章标题: {article.get('title', '无标题')}")
            print(f"✅ 图片URL: {article.get('coverImageUrl', '无')}")
            print(f"✅ 发布时间: {article.get('publishedAt', '无')}")
            print(f"✅ Slug: {article.get('slug', '无')}")
            return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_sota():
    """测试SOTA开源项目API"""
    print("\n" + "=" * 80)
    print("测试SOTA开源项目API")
    print("=" * 80)
    try:
        url = "https://sota.jiqizhixin.com/api/v2/sota/terms?order=generationAt&per=8&page=1"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        # 使用修复后的解析逻辑
        projects = data.get('data', [])
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 获取到 {len(projects)} 个项目")
        
        if projects:
            project = projects[0]
            source = project.get('source', {})
            print(f"✅ 第一个项目名称: {source.get('name', '无')}")
            print(f"✅ 项目slug: {source.get('slug', '无')}")
            print(f"✅ 项目描述长度: {len(source.get('summary', ''))}")
            return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_chinaz():
    """测试站长之家API"""
    print("\n" + "=" * 80)
    print("测试站长之家实时新闻API")
    print("=" * 80)
    try:
        url = "https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type=1&page=1&pagesize=20"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://app.chinaz.com/',
            'Accept': 'application/json, text/plain, */*',
        }
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        # 使用修复后的解析逻辑
        if isinstance(data, list):
            news_list = data
        else:
            news_list = data.get('data', [])
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 数据类型: {type(data).__name__}")
        print(f"✅ 获取到 {len(news_list)} 条新闻")
        
        if news_list:
            news = news_list[0]
            print(f"✅ 第一条新闻标题: {news.get('title', '无')}")
            print(f"✅ 新闻ID: {news.get('Id', '无')}")
            print(f"✅ 图片URL: {news.get('thumb', '无')}")
            print(f"✅ 描述: {news.get('description', '无')[:50]}...")
            return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("\n🔍 开始验证新闻资讯API修复情况...\n")
    
    results = {
        "机器之心": test_jiqizhixin(),
        "SOTA开源项目": test_sota(),
        "站长之家": test_chinaz()
    }
    
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("🎉 所有测试通过！" if all_passed else "⚠️  部分测试失败"))
