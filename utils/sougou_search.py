import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
from datetime import datetime, timedelta
import hashlib
import urllib.parse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    # 初始化一个空列表来存储数据
    data = []
    # 用于去重的链接集合
    seen_links = set()

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
        
        # 检查链接是否已经存在，如果不存在则添加到数据列表中
        if h3_link and h3_link not in seen_links:
            seen_links.add(h3_link)
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
    # 返回标题和链接的列表
    return [{'title': item[0], 'url': item[1]} for item in data if item[1]]

def normalize_url(url):
    """
    规范化URL，去除查询参数、锚点等，便于比较
    """
    if not url:
        return ""
        
    try:
        # 解析URL
        parsed = urllib.parse.urlparse(url)
        
        # 构建基本URL（协议 + 域名 + 路径）
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # 移除尾部斜杠
        if normalized.endswith('/'):
            normalized = normalized[:-1]
            
        return normalized.lower()  # 转为小写以忽略大小写差异
    except Exception as e:
        logger.warning(f"URL规范化失败: {url}, 错误: {str(e)}")
        return url.lower()

def calculate_url_hash(url):
    """
    计算URL的哈希值，用于快速比较
    """
    if not url:
        return ""
        
    try:
        # 规范化URL
        normalized_url = normalize_url(url)
        # 计算MD5哈希
        return hashlib.md5(normalized_url.encode('utf-8')).hexdigest()
    except Exception as e:
        logger.warning(f"URL哈希计算失败: {url}, 错误: {str(e)}")
        return ""

def is_similar_url(url1, url2):
    """
    判断两个URL是否相似（基于规范化后的URL）
    """
    if not url1 or not url2:
        return False
        
    # 规范化URL
    norm_url1 = normalize_url(url1)
    norm_url2 = normalize_url(url2)
    
    # 完全相同
    if norm_url1 == norm_url2:
        return True
    
    # 检查一个是否是另一个的子路径
    if norm_url1 in norm_url2 or norm_url2 in norm_url1:
        return True
        
    # 检查域名是否相同，路径是否相似
    parsed1 = urllib.parse.urlparse(norm_url1)
    parsed2 = urllib.parse.urlparse(norm_url2)
    
    # 如果域名相同且路径相似度高
    if parsed1.netloc == parsed2.netloc:
        # 检查路径相似度
        path1 = parsed1.path.strip('/')
        path2 = parsed2.path.strip('/')
        
        # 如果路径完全相同或一个是另一个的子路径
        if path1 == path2 or path1.startswith(path2) or path2.startswith(path1):
            return True
            
    return False

def deduplicate_results(results):
    """
    对搜索结果进行去重
    """
    if not results:
        return []
        
    # 用于跟踪已处理的URL
    processed_urls = set()
    # 用于存储去重后的结果
    unique_results = []
    # 用于存储规范化URL到原始结果的映射
    url_hash_map = {}
    
    # 首先基于URL哈希去重
    for result in results:
        if not result.get('url'):
            continue
            
        url = result['url']
        url_hash = calculate_url_hash(url)
        
        if url_hash and url_hash not in url_hash_map:
            url_hash_map[url_hash] = result
            unique_results.append(result)
        else:
            logger.info(f"发现重复URL (哈希): {url}")
    
    # 然后基于URL相似度进行进一步去重
    final_results = []
    for result in unique_results:
        url = result['url']
        normalized_url = normalize_url(url)
        
        # 检查是否与已处理的URL相似
        is_duplicate = False
        for processed_url in processed_urls:
            if is_similar_url(normalized_url, processed_url):
                logger.info(f"发现相似URL: {url} 与 {processed_url}")
                is_duplicate = True
                break
                
        if not is_duplicate:
            processed_urls.add(normalized_url)
            final_results.append(result)
    
    logger.info(f"搜索结果去重: 原始数量={len(results)}, 去重后数量={len(final_results)}")
    return final_results

def query_search(question: str, remove_duplicates=True):
    """
    搜索函数，获取搜狗搜索结果并进行去重
    :param question: 查询问题
    :param remove_duplicates: 是否去除重复结果，默认为True
    :return: 搜索结果列表
    """
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
    
    try:
        response = requests.get(url, params=params, headers=headers)
        result = response.text
        search_results = text_from_html(result)
        
        # 如果需要去重
        if remove_duplicates and search_results:
            return deduplicate_results(search_results)
        return search_results
    except Exception as e:
        logger.error(f"搜狗搜索失败: {str(e)}")
        return []

if __name__ == "__main__":
    print(query_search("如何使用python爬虫"))