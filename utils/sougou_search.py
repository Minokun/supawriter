import requests
from bs4 import BeautifulSoup
from bs4.element import Comment

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

        # 提取<p>标签中的内容
        p = div.find('p', class_='txt-info')
        p_text = p.get_text(strip=True) if p else ''

        # 提取<span>标签中的内容
        span = div.find('span', class_='all-time-y2')
        span_text = span.get_text(strip=True) if span else ''

        # 提取时间
        article_time = div.find('span', class_='s2').get_text(strip=True) if span else ''


        # 将提取的信息添加到数据列表中
        data.append([h3_text, h3_link, p_text, span_text, article_time])
    print(data)
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
    text_from_html(result)

if __name__ == "__main__":
    query_search("如何使用python爬虫")