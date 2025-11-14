#!/usr/bin/env python3
"""
每日新闻生成脚本
从机器之心和站长之家API获取昨天到今天的新闻，生成公众号文章格式
"""

import requests
import json
import os
from datetime import datetime, timedelta
import re
import html

def clean_text(text):
    """清理文本内容，移除HTML标签和多余空白"""
    if not text:
        return ""
    
    # 1. HTML解码
    text = html.unescape(text)
    # 2. 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text, flags=re.DOTALL)
    # 3. 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fetch_jiqizhixin_news():
    """获取机器之心文章"""
    print("正在获取机器之心新闻...")
    try:
        # 获取更多文章以便筛选昨天到今天的
        url = "https://www.jiqizhixin.com/api/article_library/articles.json?sort=time&page=1&per=50"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            # 筛选昨天到今天的文章
            yesterday = datetime.now() - timedelta(days=1)
            today = datetime.now()
            
            filtered_articles = []
            for article in articles:
                published_at = article.get('publishedAt', '')
                if published_at:
                    try:
                        # 机器之心API返回格式: "2025/11/10 14:16"
                        dt = datetime.strptime(published_at, '%Y/%m/%d %H:%M')
                        # 检查是否在昨天到今天的范围内
                        if yesterday.date() <= dt.date() <= today.date():
                            filtered_articles.append(article)
                            print(f"  ✓ 包含文章: {article.get('title', '无标题')[:50]}... ({published_at})")
                        else:
                            print(f"  ✗ 跳过文章: {article.get('title', '无标题')[:50]}... ({published_at}) - 超出时间范围")
                    except Exception as e:
                        # 如果时间解析失败，跳过这篇文章
                        print(f"  ⚠ 时间解析失败: {article.get('title', '无标题')[:50]}... ({published_at}) - {e}")
                        continue
                else:
                    # 没有发布时间的文章也跳过
                    print(f"  ⚠ 无发布时间: {article.get('title', '无标题')[:50]}...")
                    continue
            
            print(f"获取到 {len(filtered_articles)} 篇机器之心文章")
            return filtered_articles
        else:
            print(f"获取机器之心数据失败，状态码：{response.status_code}")
            return []
    except Exception as e:
        print(f"获取机器之心新闻失败：{str(e)}")
        return []

def fetch_chinaz_news():
    """获取站长之家实时新闻"""
    print("正在获取实时新闻...")
    try:
        # type=1 表示实时新闻
        url = "https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type=1&page=1&pagesize=50"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://app.chinaz.com/',
            'Accept': 'application/json, text/plain, */*',
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # 站长之家API直接返回数组
            if isinstance(data, list):
                news_list = data
            else:
                news_list = data.get('data', [])
            
            # 由于站长之家API没有明确的时间筛选，我们取前20条作为最新新闻
            filtered_news = news_list[:20] if news_list else []
            
            print(f"获取到 {len(filtered_news)} 条实时新闻")
            return filtered_news
        else:
            print(f"获取实时新闻数据失败，状态码：{response.status_code}")
            return []
    except Exception as e:
        print(f"获取实时新闻失败：{str(e)}")
        return []

def format_jiqizhixin_article(article):
    """格式化机器之心文章为markdown"""
    title = clean_text(article.get('title', '无标题'))
    summary = clean_text(article.get('content', '暂无摘要'))
    image_url = article.get('coverImageUrl', '')
    published_at = article.get('publishedAt', '')
    
    # 格式化时间
    time_str = "未知时间"
    if published_at:
        try:
            # 机器之心API返回格式: "2025/11/10 14:16"
            dt = datetime.strptime(published_at, '%Y/%m/%d %H:%M')
            time_str = dt.strftime('%Y-%m-%d %H:%M')
        except:
            # 如果解析失败，直接使用原始时间字符串
            time_str = published_at
    
    # 生成markdown格式
    markdown = f"### {title}\n\n"
    if image_url:
        markdown += f"![{title}]({image_url})\n\n"
    if summary:
        markdown += f"{summary}\n\n"
    markdown += f"**发布时间：** {time_str}\n\n---\n\n"
    
    return markdown

def format_chinaz_news(news):
    """格式化站长之家新闻为markdown"""
    title = clean_text(news.get('title', '无标题'))
    description = clean_text(news.get('description', ''))
    summary = clean_text(news.get('summary', ''))
    thumb = news.get('thumb', '')
    addtime = clean_text(news.get('addtime', '最新'))
    
    # 使用description或summary作为内容
    content = description if description else summary
    if not content:
        content = "暂无详细描述"
    
    # 生成markdown格式
    markdown = f"### {title}\n\n"
    if thumb:
        markdown += f"![{title}]({thumb})\n\n"
    markdown += f"{content}\n\n"
    markdown += f"**发布时间：** {addtime}\n\n---\n\n"
    
    return markdown

def generate_daily_news_article():
    """生成每日新闻文章"""
    print("开始生成每日新闻文章...")
    
    # 获取新闻数据
    jiqizhixin_articles = fetch_jiqizhixin_news()
    chinaz_news = fetch_chinaz_news()
    
    if not jiqizhixin_articles and not chinaz_news:
        print("未获取到任何新闻数据，退出生成")
        return
    
    # 生成文章标题和日期
    today = datetime.now()
    date_str = today.strftime('%Y年%m月%d日')
    filename_date = today.strftime('%Y%m%d')
    
    # 开始构建文章内容
    article_content = f"""# AI新闻快速总览 - {date_str}

> **每日AI资讯精选**  
> 汇聚最新AI技术动态、行业资讯和前沿研究  
> 生成时间：{today.strftime('%Y-%m-%d %H:%M:%S')}

---

"""
    
    # 添加AI专题新闻（机器之心）
    if jiqizhixin_articles:
        article_content += f"""## 🤖 AI专题新闻

> 精选 {len(jiqizhixin_articles)} 篇专业AI技术资讯

"""
        
        for i, article in enumerate(jiqizhixin_articles, 1):
            article_content += format_jiqizhixin_article(article)
    
    # 添加实时新闻
    if chinaz_news:
        article_content += f"""## 📰 实时新闻

> 精选 {len(chinaz_news)} 条最新AI行业动态

"""
        
        for i, news in enumerate(chinaz_news, 1):
            article_content += format_chinaz_news(news)
    
    # 添加文章结尾
    article_content += f"""---

## 📊 今日数据统计

- **AI专题新闻：** {len(jiqizhixin_articles)} 篇
- **实时新闻：** {len(chinaz_news)} 条
- **总计：** {len(jiqizhixin_articles) + len(chinaz_news)} 条资讯
- **生成时间：** {today.strftime('%Y-%m-%d %H:%M:%S')}

---

*本文由AI新闻聚合系统自动生成*

**关注我们，获取更多AI资讯！**
"""
    
    # 保存文章到文件
    output_dir = "/Users/wxk/Desktop/workspace/supawriter/data/daily_news"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"AI新闻快速总览_{filename_date}.md"
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article_content)
        
        print(f"✅ 每日新闻文章已生成：{filepath}")
        print(f"📊 统计信息：")
        print(f"   - AI专题新闻：{len(jiqizhixin_articles)} 篇")
        print(f"   - 实时新闻：{len(chinaz_news)} 条")
        print(f"   - 文章总长度：{len(article_content)} 字符")
        
        return filepath
        
    except Exception as e:
        print(f"❌ 保存文章失败：{str(e)}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 每日AI新闻生成器")
    print("=" * 60)
    
    # 生成每日新闻文章
    result = generate_daily_news_article()
    
    if result:
        print(f"\n🎉 任务完成！文章已保存到：{result}")
    else:
        print("\n❌ 任务失败！")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
