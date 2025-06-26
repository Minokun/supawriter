import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
from datetime import datetime, timedelta

def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    # 初始化一个空列表来存储数据
    data = []

    # 找到所有的<li>标签
    for div in soup.find_all('div', class_='txt-box'):
        # 提取<h3>标签中的内容和链接
        h3 = div.find('h3')
        h3_text = h3.get_text(strip=True)
        h3_link = h3.find('a')['href'] if h3.find('a') else ''
        # 检查链接是否是相对路径，如果是则添加域名前缀
        if h3_link.startswith('/link?'):
            h3_link = 'https://weixin.sogou.com' + h3_link

        # 提取<p>标签中的内容
        p = div.find('p', class_='txt-info')
        p_text = p.get_text(strip=True) if p else ''

        # 提取<span>标签中的内容
        span = div.find('span', class_='all-time-y2')
        span_text = span.get_text(strip=True) if span else ''

        # 尝试提取时间戳（在JavaScript中）
        time_script = div.find('span', class_='s2').find('script')
        timestamp = ''
        if time_script and 'timeConvert' in time_script.text:
            # 从脚本中提取时间戳
            import re
            timestamp_match = re.search(r"timeConvert\('(\d+)'\)", time_script.text)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
        
        # 将提取的信息添加到数据列表中
        data.append([h3_text, h3_link, p_text, span_text, timestamp])
    
    # 获取当前时间
    current_time = datetime.now()
    # 计算一年前的时间
    one_year_ago = current_time - timedelta(days=180)
    
    # 筛选最近一年的数据
    recent_data = []
    for item in data:
        if item[4]:  # 检查时间戳是否存在
            try:
                # 将时间戳转换为datetime对象
                item_time = datetime.fromtimestamp(int(item[4]))
                # 如果时间在一年内，则添加到结果中
                if item_time >= one_year_ago:
                    recent_data.append(item)
            except (ValueError, TypeError):
                # 如果时间戳无效，仍然保留该项
                recent_data.append(item)
        else:
            # 如果没有时间戳，也保留该项
            recent_data.append(item)

    # 使用筛选后的数据
    data = recent_data
    # 返回链接而不是时间
    return [item[0] for item in data]

def query_search(question: str):
    # 优化询问的问题
    # question = chat(question, "根据我的问题重新整理格式并梳理成搜索引擎的查询问题，要求保留原文语意。使用中文。")
    # 搜索
    url = "https://weixin.sogou.com/weixin"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
    }
    params = {
        "query": question,
        "ie": "utf8",
        "type": "2"
    }
    response = requests.get(url, params=params, headers=headers)
    result = response.text
    return text_from_html(result)

if __name__ == "__main__":
    print(query_search("如何使用python爬虫"))