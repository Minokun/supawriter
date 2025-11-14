# 导入所需的库
# 将当前目录加入环境变量
import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 标准库
import json
import time
import requests
import random
import re
import urllib3
import logging
import hashlib
import threading
import asyncio
import concurrent.futures
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True  # Python 3.8+ 强制重新配置，确保在多模块环境中生效
)
logger = logging.getLogger(__name__)

# 禁用SSL警告
urllib3.disable_warnings()

# ----------------------
# URL 规范化与相似性判断工具（替代 sougou_search）
# ----------------------
def normalize_url(url: str) -> str:
    """将 URL 进行规范化，便于去重与相似性判断。
    规则：
    - 小写 scheme 和 host
    - 去除 fragment
    - 去除常见追踪参数（utm_*、gclid、fbclid 等）
    - 规范化路径的多余斜杠与结尾斜杠
    - 对于无效 URL，返回原始字符串以避免崩溃
    """
    try:
        pr = urlparse(url)
        scheme = (pr.scheme or 'http').lower()
        netloc = pr.netloc.lower()

        # 规范化路径：去除多余斜杠
        path = re.sub(r'/+', '/', pr.path or '/')
        # 移除结尾斜杠，根路径保留 '/'
        if path != '/' and path.endswith('/'):
            path = path[:-1]

        # 清理查询参数
        tracking_keys = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'gclid', 'fbclid', 'igshid', 'spm', 'mkt_tok'
        }
        query_pairs = [(k, v) for k, v in parse_qsl(pr.query, keep_blank_values=True) if k not in tracking_keys]
        # 按键排序，避免顺序影响去重
        query_pairs.sort(key=lambda x: x[0])
        query = urlencode(query_pairs, doseq=True)

        # 去除 fragment
        fragment = ''

        normalized = urlunparse((scheme, netloc, path, '', query, fragment))
        return normalized
    except Exception:
        return url


def is_similar_url(a: str, b: str) -> bool:
    """判断两个 URL 是否相似。
    规则：
    - 完全相等直接相似
    - 域名与路径相同（忽略查询参数顺序与追踪参数）判定为相似
    - 常见的 www 前缀差异等也视为相似
    """
    na = normalize_url(a)
    nb = normalize_url(b)
    if na == nb:
        return True
    pra, prb = urlparse(na), urlparse(nb)
    # 去掉 www 前缀对比
    host_a = pra.netloc[4:] if pra.netloc.startswith('www.') else pra.netloc
    host_b = prb.netloc[4:] if prb.netloc.startswith('www.') else prb.netloc
    if host_a != host_b:
        return False
    # 路径一致则认为相似（查询参数差异忽略）
    return pra.path == prb.path

# 本地导入
from settings import base_path, LLM_MODEL, DEFAULT_SPIDER_NUM, SERPER_API_KEY
from grab_html_content import get_main_content
from utils.llm_chat import chat
import prompt_template
from utils.embedding_utils import (
    Embedding,
    add_batch_embeddings_to_faiss_index,
    save_faiss_index,
    add_to_faiss_index,
)
from utils.embedding_utils import create_faiss_index
from utils.image_search_indexer import index_ddgs_images
from utils.serper_search import serper_search
from utils.ddgs_utils import search_ddgs

max_workers = 20

SERPER_RESULT_LIMIT = 10  # 固定保留的 Serper 搜索结果数量

# 注意：不再使用全局URL去重，改为任务级别的去重，确保每次文章生成都是独立的搜索
# GLOBAL_PROCESSED_URLS = set()  # 已移除全局去重

def process_result(content, question, output_type=prompt_template.ARTICLE, model_type='deepseek', model_name='deepseek-chat'):
    """
    处理单个搜索结果，生成摘要
    :param content: 搜索结果字典
    :param question: 查询问题
    :param output_type: 输出类型
    :return: 摘要内容
    """
    # print(f'字数统计：{len(content)}')
    if len(content) < 30000:
        html_content = content
    else:
        html_content = content[:30000]
    # 创建对话提示
    # 这里不捕获异常，让它向上传播
    logger.debug(f"处理任务: 模型={model_type}/{model_name}, 内容长度={len(html_content)}")
    chat_result = chat(f'## 参考的上下文资料：<content>{html_content}</content> ## 请严格依据topic完成相关任务：<topic>{question}</topic> ', output_type, model_type, model_name)
    logger.debug(f"任务完成: 结果长度={len(chat_result)}")
    # print(f'总结后的字数统计：{len(chat_result)}')
    return chat_result


from typing import Optional

def llm_task(search_result, question, output_type, model_type, model_name, max_workers=20, progress_callback: Optional[callable] = None):
    """
    使用线程池并发处理搜索结果，并提供进度回调
    :param search_result: 搜索结果列表
    :param question: 查询问题
    :param output_type: 输出类型
    :param model_type: 模型类型
    :param model_name: 模型名称
    :param max_workers: 最大线程数
    :param progress_callback: 进度回调函数，接收 (completed_count, total_count)
    :return: 处理后的结果
    """
    if model_type == 'glm':
        max_workers = 10
    
    task_description = ""
    if "---任务---" in output_type:
        task_parts = output_type.split("---任务---")
        if len(task_parts) > 1:
            task_description = task_parts[1].split("---")[0].strip()
    
    logger.info(f"开始处理LLM任务: 模型={model_type}/{model_name}, 任务类型=---任务---{task_description}---, 搜索结果数量={len(search_result)}")
    
    MAX_CONTENT_LENGTH = 30000
    optimized_search_result = []
    current_chunk = ""
    current_titles = []
    current_urls = []
    
    # 计算内容相关性得分
    def calculate_relevance_score(content, title, query):
        # 提取查询中的关键词
        query_keywords = set(re.findall(r'\w+', query.lower()))
        # 移除常见的停用词
        stopwords = {'的', '了', '和', '与', '或', '在', '是', '有', '什么', '如何', '怎么', 'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for'}
        query_keywords = query_keywords - stopwords
        
        # 计算标题中关键词匹配数
        title_score = sum(1 for keyword in query_keywords if keyword in title.lower()) * 2
        
        # 计算内容中关键词匹配数（只检查前1000个字符以提高效率）
        content_preview = content[:1000].lower()
        content_score = sum(1 for keyword in query_keywords if keyword in content_preview)
        
        # 计算总分
        return title_score + content_score
    
    # 为每个结果添加相关性得分
    for item in search_result:
        content = item.get('html_content', '')
        title = item.get('title', 'Untitled')
        item['relevance_score'] = calculate_relevance_score(content, title, question)
    
    # 首先按相关性得分排序（降序），然后按内容长度排序（升序）
    sorted_results = sorted(search_result, 
                           key=lambda x: (-x.get('relevance_score', 0), len(x.get('html_content', ''))))
    
    for item in sorted_results:
        content = item.get('html_content', '')
        title = item.get('title', 'Untitled')
        
        # 记录处理的内容信息
        logger.debug(f"处理搜索结果: 标题='{title[:30]}...', 内容长度={len(content)}, 相关性得分={item.get('relevance_score', 0)}")
        
        if len(content) >= MAX_CONTENT_LENGTH:
            # 对于大型内容，保留原始URL和相关性得分
            optimized_search_result.append({
                'title': title, 
                'html_content': content[:MAX_CONTENT_LENGTH], 
                'url': item.get('url', ''),
                'relevance_score': item.get('relevance_score', 0),
                'is_truncated': True
            })
            continue
        
        if len(current_chunk) + len(content) > MAX_CONTENT_LENGTH:
            if current_chunk:
                # 计算组合内容的平均相关性得分
                avg_relevance = sum(search_result[i].get('relevance_score', 0) 
                                  for i, _ in enumerate(search_result) 
                                  if search_result[i].get('url', '') in current_urls) / len(current_urls) if current_urls else 0
                
                optimized_search_result.append({
                    'title': ' | '.join(current_titles), 
                    'html_content': current_chunk, 
                    'url': 'combined', 
                    'source_urls': current_urls,
                    'relevance_score': avg_relevance,
                    'combined_count': len(current_urls)
                })
            current_chunk = content
            current_titles = [title]
            current_urls = [item.get('url', '')]
        else:
            if current_chunk:
                # 使用更清晰的分隔符，包含标题信息
                separator = f"\n\n{'='*40}\n## {title}\n{'='*40}\n\n"
                current_chunk += separator
            else:
                # 第一个内容添加标题
                current_chunk = f"## {title}\n\n"
            current_chunk += content
            current_titles.append(title)
            current_urls.append(item.get('url', ''))
    
    if current_chunk:
        # 计算组合内容的平均相关性得分
        avg_relevance = sum(search_result[i].get('relevance_score', 0) 
                          for i, _ in enumerate(search_result) 
                          if search_result[i].get('url', '') in current_urls) / len(current_urls) if current_urls else 0
        
        optimized_search_result.append({
            'title': ' | '.join(current_titles), 
            'html_content': current_chunk, 
            'url': 'combined', 
            'source_urls': current_urls,
            'relevance_score': avg_relevance,
            'combined_count': len(current_urls)
        })
    
    # 记录优化详情
    top_relevance = sorted([item.get('relevance_score', 0) for item in search_result], reverse=True)[:5] if search_result else []
    # 计算优化前后的字数变化
    original_length = sum(len(item.get('html_content', '')) for item in search_result)
    optimized_length = sum(len(item.get('html_content', '')) for item in optimized_search_result)
    length_diff = optimized_length - original_length
    
    logger.info(f"搜索结果优化: 原始数量={len(search_result)}, 优化后数量={len(optimized_search_result)}, "
                f"前5相关性得分={top_relevance}, 字数变化={length_diff:+}, "
                f"原字数={original_length}, 优字数={optimized_length}")
    connection_error = None
    
    def process_result_wrapper(content, question, output_type, model_type, model_name):
        nonlocal connection_error
        if connection_error: return "CONNECTION_ERROR"
        try:
            return process_result(content, question, output_type, model_type, model_name)
        except ConnectionError as e:
            connection_error = e
            logger.error(f"连接错误: {str(e)}")
            return "CONNECTION_ERROR"

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_result_wrapper, item['html_content'], question, output_type, model_type, model_name) 
                  for item in optimized_search_result]
        
        logger.info(f"已提交{len(futures)}个LLM任务到线程池，等待完成...")
        
        completed_count = 0
        total_count = len(futures)

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if connection_error:
                logger.error(f"检测到连接错误，正在中止其余任务...")
                break 

            results.append(result)
            completed_count += 1
            if progress_callback:
                try:
                    progress_callback(completed_count, total_count)
                except Exception as e:
                    logger.error(f"进度回调函数出错: {e}")

    if connection_error:
        logger.error(f"任务执行因连接错误而失败: {str(connection_error)}")
        raise connection_error
    
    logger.info(f"所有LLM任务已完成，获取到{len(results)}个结果")
    
    if output_type == prompt_template.ARTICLE_OUTLINE_GEN:
        outlines = '\n'.join([res.replace('\n', '').replace('```json', '').replace('```', '') for res in results if res != "CONNECTION_ERROR"])
        logger.info(f"大纲结果合并完成，总长度={len(outlines)}")
        return outlines
    else:
        outlines = '\n'.join([res for res in results if res != "CONNECTION_ERROR"])
        if len(outlines) > MAX_CONTENT_LENGTH:
            logger.info(f"结果过长({len(outlines)}字符)，截断至{MAX_CONTENT_LENGTH}字符")
            outlines = outlines[:MAX_CONTENT_LENGTH]
        return outlines

class Search:
    def __init__(self, result_num=DEFAULT_SPIDER_NUM):
        """
        初始化搜索引擎类，使用 DDGS + Serper 双引擎搜索
        :param result_num: DDGS 搜索结果数量，默认为 DEFAULT_SPIDER_NUM (30)
                          Serper 固定返回 10 条结果
        """
        self.result_num = result_num  # DDGS 结果数量
        self.search_query = ""  # 原始查询词
        self.optimized_query = ""  # 优化后的查询词

    def deduplicate_urls(self, urls_with_data, key='url'):
        """
        在当前批次内去除重复URL，使用高级URL标准化和相似性检查
        注意：不再使用全局去重，确保每次文章生成都是独立的搜索
        
        Args:
            urls_with_data: List of dictionaries containing URLs and associated data
            key: The dictionary key containing the URL
            
        Returns:
            List of dictionaries with duplicate URLs removed
        """
        if not urls_with_data:
            return []
            
        # Track processed URLs for this batch
        processed_urls = set()
        unique_results = []
        
        for item in urls_with_data:
            if not item.get(key):
                continue
                
            url = item[key]
            normalized_url = normalize_url(url)
            
            # 不再检查全局已处理URL，确保每次搜索都是独立的
            # 原全局去重逻辑已移除，避免跨用户和跨任务的数据污染
                
            # Skip if URL has been processed in this batch
            is_duplicate = False
            for processed_url in processed_urls:
                if is_similar_url(normalized_url, processed_url):
                    logger.info(f"Skipping similar URL in batch: {url} similar to {processed_url}")
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                processed_urls.add(normalized_url)
                # 不再添加到全局集合，保持任务独立性
                # GLOBAL_PROCESSED_URLS.add(normalized_url)  # 已移除
                unique_results.append(item)
                
        logger.info(f"URL deduplication: Original={len(urls_with_data)}, After deduplication={len(unique_results)}")
        return unique_results
        
    def query_search(self, query: str):
        """
        发送请求到搜索引擎，获取JSON响应
        整合 DDGS 和 Serper 搜索结果
        :param query: 查询词（已优化）
        :return: JSON数据，包含合并后的搜索结果
        """
        all_results = []
        ddgs_count = 0
        serper_count = 0
        
        # 1. 使用 DDGS (DuckDuckGo Search) 搜索
        try:
            logger.info(f"DDGS 搜索开始: {query}, 最大结果数: {self.result_num}")
            ddgs_raw_results = search_ddgs(query, search_type="text", max_results=self.result_num)
            
            # 转换 DDGS 结果为统一格式
            ddgs_results = []
            for idx, item in enumerate(ddgs_raw_results):
                formatted_item = {
                    'title': item.get('title', ''),
                    'url': item.get('href', ''),  # DDGS 使用 'href'
                    'content': item.get('body', ''),  # DDGS 使用 'body'
                    'score': 1.0 - idx * 0.03,  # 根据位置计算分数
                    'source': 'ddgs'  # 标记来源
                }
                ddgs_results.append(formatted_item)
            
            ddgs_count = len(ddgs_results)
            logger.info(f"DDGS 搜索结果: {ddgs_count} 条")
            all_results.extend(ddgs_results)
        except Exception as e:
            logger.error(f"DDGS 搜索失败: {e}")
        
        # 2. 使用 Serper 搜索引擎（仅当 API Key 有效时）
        if SERPER_API_KEY:
            try:
                logger.info(f"Serper 搜索开始: query='{query}'")
                serper_results = serper_search(
                    api_key=SERPER_API_KEY,
                    query=query,
                    gl="cn",
                    hl="zh-cn",
                    time_range="y"  # 一年内的结果
                )
                
                if serper_results:
                    serper_count = len(serper_results)
                    logger.info(f"Serper 搜索结果: {serper_count} 条")
                    all_results.extend(serper_results)
                else:
                    logger.warning("Serper 搜索返回空列表")
            except Exception as e:
                logger.error(f"Serper 搜索失败: {e}", exc_info=True)
        else:
            logger.info("Serper API Key 未配置，跳过 Serper 搜索")
        
        # 3. 返回合并后的结果
        logger.info(f"合并搜索结果: DDGS ({ddgs_count}) + Serper ({serper_count}) = 总计 {len(all_results)} 条")
        return {'results': all_results}

    def get_search_result(self, question: str, is_multimodal=False, use_direct_image_embedding=False, theme="", spider_mode=False, progress_callback: Optional[callable] = None, username: str = None, article_id: str = None):
        # 先优化查询词，提取关键词
        self.search_query = question
        optimizeq = chat(question, system_prompt="""你是搜索引擎查询优化专家。请将用户的问题转换为更适合搜索引擎的查询词。
                优化规则：
                1. 提取核心关键词和概念，去除无关的停用词（如"请问"、"怎么"、"如何"等）
                2. 保留专业术语、品牌名称、技术名词的完整性
                3. 关键词之间使用空格分隔，不要使用引号、括号等特殊符号
                4. 保持查询词简洁自然，避免过于复杂的搜索语法
                5. 保留年份、版本号等重要限定词

                直接输出优化后的查询词，不要解释，不要添加引号。""")
        logger.info(f"优化后的搜索词: {optimizeq}")
        self.optimized_query = optimizeq
        
        # 从原始查询文本和优化后的查询中提取关键词
        original_keywords = set(re.findall(r'\w+', question))
        optimized_keywords = set(re.findall(r'\w+', optimizeq))
        important_keywords = original_keywords.union(optimized_keywords)
        
        # 使用优化后的查询词进行搜索
        data = self.query_search(optimizeq)
        search_result = []
        search_engine_urls = []
        
        # 检查是否有搜索结果
        if data and data.get('results'):
            logger.info(f"开始处理合并后的搜索结果: {len(data['results'])} 条")
            
            # 注释：不在此处直接添加结果，而是在下面进行相关性评分后再添加
            # 避免重复添加导致结果数量翻倍
            # search_engine_items = []
            # for item in data['results']:
            #     if 'url' in item:
            #         search_engine_urls.append(item['url'])
            #         search_engine_items.append({
            #             'title': item.get('title', ''),
            #             'url': item['url'],
            #             'html_content': '',
            #         })
            # search_engine_items = self.deduplicate_urls(search_engine_items)
            # search_result.extend(search_engine_items)
            
            # 将结果按相关性评分排序（同时进行URL去重）
            scored_results = []
            seen_urls = set()  # 用于去重
            
            for i in data['results']:
                # 跳过特定文件类型和低分结果
                if i['url'].split('.')[-1] in ['xlsx', 'pdf', 'doc', 'docx', 'xls', 'ppt', 'pptx']:
                    continue
                if i['score'] < 0.21:
                    continue
                
                # URL去重检查
                normalized_url = normalize_url(i['url'])
                if normalized_url in seen_urls:
                    logger.debug(f"跳过重复URL: {i['url']}")
                    continue
                seen_urls.add(normalized_url)
                    
                # 计算关键词匹配度
                title_keywords = set(re.findall(r'\w+', i.get('title', '').lower()))
                content_keywords = set(re.findall(r'\w+', i.get('content', '').lower()))
                
                # 获取标题和内容中与查询关键词的重叠数
                title_match = len(title_keywords.intersection(important_keywords))
                content_match = len(content_keywords.intersection(important_keywords))
                
                # 基于原始分数和关键词匹配度的综合分数
                relevance_score = (i['score'] * 0.4) + (title_match * 0.4) + (content_match * 0.2)
                    
                scored_results.append((i, relevance_score))
            
            logger.info(f"相关性评分: 原始 {len(data['results'])} 条 -> 过滤后 {len(scored_results)} 条（已去重、过滤低分和特殊文件）")
                
            # 按相关性分数降序排序
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # 提取排序后的结果（DDGS 仅受 DEFAULT_SPIDER_NUM 限制，Serper 固定保留 ~10 条）
            selected_results = []
            ddgs_selected = 0
            serper_selected = 0
            serper_limit = SERPER_RESULT_LIMIT if SERPER_RESULT_LIMIT else None

            for item, score in scored_results:
                source = item.get('source', 'ddgs')
                if source == 'serper':
                    if serper_limit is not None and serper_selected >= serper_limit:
                        continue
                    serper_selected += 1
                else:
                    if ddgs_selected >= self.result_num:
                        continue
                    ddgs_selected += 1
                selected_results.append((item, score))

            for i, score in selected_results:
                url_display = i['url'][:37] + '...' if len(i['url']) > 40 else i['url']
                print(f"{url_display} - 相关度: {score:.2f} - {i['title']}")
                search_result.append({
                    'title': i['title'], 
                    'url': i['url'], 
                    'html_content': i['content'] if 'content' in i else '',
                    'relevance_score': score,
                    'source': i.get('source', 'ddgs')
                })
                search_engine_urls.append(i['url'])

            serper_limit_display = serper_limit if serper_limit is not None else '不限'
            logger.info(
                "相关性排序后选取 DDGS %d 条 (限制=%d) + Serper %d 条 (限制=%s)，实际添加: %d 条",
                ddgs_selected,
                self.result_num,
                serper_selected,
                serper_limit_display,
                len(selected_results)
            )
            # 获取网页主要内容 - 始终爬取所有URL
            if len(search_engine_urls) > 0:
                # 在爬取内容前，确保所有URL都已去重
                final_urls = []
                final_url_map = {}
                
                # 构建最终去重的URL列表
                for item in search_result:
                    url = item['url']
                    normalized_url = normalize_url(url)
                    
                    # 如果URL还未被处理，添加到最终列表
                    if normalized_url not in final_url_map:
                        final_urls.append(url)
                        final_url_map[normalized_url] = url
                
                # 限制最终抓取数量：DDGS 受 DEFAULT_SPIDER_NUM 限制，Serper 全部保留
                allowed_fetch = ddgs_selected + serper_selected
                if len(final_urls) > allowed_fetch:
                    final_urls = final_urls[:allowed_fetch]
                logger.info(
                    "Final deduplicated URLs for content grabbing (DDGS %d + Serper %d = %d): %d",
                    ddgs_selected,
                    serper_selected,
                    allowed_fetch,
                    len(final_urls)
                )
                
                # 爬取内容
                result, task_id = asyncio.run(get_main_content(final_urls, is_multimodal=is_multimodal, use_direct_image_embedding=use_direct_image_embedding, theme=theme, progress_callback=progress_callback, username=username, article_id=article_id))
                
                # 创建字典，存储爬取到的内容和图片
                html_content_dict = {}
                image_dict = {}  # 存储每个URL对应的图片
                
                # 处理爬取结果，将内容和图片映射到URL
                for item in result:
                    # 修复：grab_html_content.py中的text_from_html函数返回的是'text'键，不是'content'键
                    content = item.get('text', '')
                    # 保留原始内容用于日志记录
                    original_content = content
                    # 仅在存储时移除空白字符，保留原始格式用于日志
                    content_for_storage = content.replace('\n', '').replace(' ', '') if content else ''
                    url = item.get('url', '')
                    original_url = item.get('original_url', url)
                    images = item.get('images', [])
                    
                    # 记录内容长度，帮助诊断零长度内容问题
                    logger.debug(f"Content for URL {url}: original length={len(original_content)}, processed length={len(content_for_storage)}")
                    
                    # 存储内容和图片
                    if content_for_storage:
                        html_content_dict[url] = content_for_storage
                        if original_url != url:
                            html_content_dict[original_url] = content_for_storage
                    else:
                        logger.debug(f"Empty content for URL: {url} (original URL: {original_url})")
                    
                    # 存储图片
                    if images:
                        image_dict[url] = images
                        if original_url != url:
                            image_dict[original_url] = images
                
                # 然后更新搜索结果中的每一项
                for item in search_result:
                    url = item['url']
                    
                    # 添加HTML内容
                    if url in html_content_dict:
                        item['html_content'] += html_content_dict[url]
                        logger.debug(f"Added content for URL: {url}, content length: {len(html_content_dict[url])}")
                    else:
                        # 尝试匹配部分URL
                        matched = False
                        for crawled_url in html_content_dict.keys():
                            # 检查URL是否为子字符串或域名匹配
                            if url in crawled_url or crawled_url in url or \
                               urlparse(url).netloc == urlparse(crawled_url).netloc:
                                item['html_content'] += html_content_dict[crawled_url]
                                logger.debug(f"Found partial match for content: {url} -> {crawled_url}, content length: {len(html_content_dict[crawled_url])}")
                                matched = True
                                break
                    
                    # 添加图片
                    if 'images' not in item:
                        item['images'] = []
                        
                    # 直接匹配
                    if url in image_dict:
                        item['images'] = image_dict[url]
                    else:
                        # 尝试部分匹配
                        matched = False
                        for crawled_url, images in image_dict.items():
                            if url in crawled_url or crawled_url in url or \
                               urlparse(url).netloc == urlparse(crawled_url).netloc:
                                item['images'] = images
                                logger.info(f"Found partial match for images: {url} -> {crawled_url}")
                # 抓取与映射完成后，触发DDGS图片补充并写入用户/文章FAISS索引（若提供）
                try:
                    # 仅在直接URL嵌入模式下进行“批量URL嵌入”；多模态模式应逐图识别，不进行批量URL嵌入
                    # 先对本次抓取到的网页图片执行批量嵌入与入库（每批最多30）
                    try:
                        if username and article_id and image_dict and (use_direct_image_embedding and not is_multimodal):
                            faiss_index = create_faiss_index(load_from_disk=True, index_dir='data/faiss', username=username, article_id=article_id)
                            # 收集所有图片URL与其来源页面
                            all_image_pairs = []  # [(img_url, page_url)]
                            for page_url, imgs in image_dict.items():
                                for img_url in imgs:
                                    if isinstance(img_url, str) and img_url.startswith(('http://', 'https://')) and not img_url.lower().endswith('.svg'):
                                        all_image_pairs.append((img_url, page_url))
                            # 去重，保持顺序
                            seen = set()
                            unique_image_pairs = []
                            for img_url, page_url in all_image_pairs:
                                if img_url not in seen:
                                    seen.add(img_url)
                                    unique_image_pairs.append((img_url, page_url))
                            if unique_image_pairs:
                                chunk_size = 30
                                batch_added = 0
                                fallback_added = 0
                                skipped = 0
                                total = len(unique_image_pairs)
                                logger.info(f"开始对抓取到的网页图片执行批量嵌入：共 {total} 张，批大小 {chunk_size}")
                                for i in range(0, total, chunk_size):
                                    chunk = unique_image_pairs[i:i+chunk_size]
                                    urls_batch = [u for (u, _) in chunk]
                                    data_batch = [{
                                        'image_url': u,
                                        'source_url': p,
                                        'source': 'searxng_crawl',
                                        'embedding_method': 'batch_image_url'
                                    } for (u, p) in chunk]
                                    try:
                                        embeddings = Embedding().get_embedding(urls_batch, is_image_url=True)
                                    except Exception as e:
                                        embeddings = []
                                        logger.warning(f"批量获取图片嵌入失败（{i}-{i+len(chunk)}）: {e}")
                                    valid_embeds = []
                                    valid_data = []
                                    if embeddings and len(embeddings) == len(urls_batch):
                                        for emb, data_obj in zip(embeddings, data_batch):
                                            if emb:
                                                valid_embeds.append(emb)
                                                valid_data.append(data_obj)
                                            else:
                                                skipped += 1
                                        if valid_embeds:
                                            before = faiss_index.get_size()
                                            add_batch_embeddings_to_faiss_index(valid_embeds, valid_data, faiss_index)
                                            added_now = faiss_index.get_size() - before
                                            batch_added += max(0, added_now)
                                    else:
                                        # 批量失败或返回数量不匹配，对每个进行回退处理
                                        logger.debug(f"批量嵌入返回无效或数量不一致，启用逐项回退（{i}-{i+len(chunk)}）")
                                        for (u, p) in chunk:
                                            try:
                                                ok = add_to_faiss_index(u, {
                                                    'image_url': u,
                                                    'source_url': p,
                                                    'source': 'searxng_crawl',
                                                    'embedding_method': 'fallback_single_image_url'
                                                }, faiss_index, auto_save=False, username=username, article_id=article_id, is_image_url=True)
                                                if ok:
                                                    fallback_added += 1
                                                else:
                                                    skipped += 1
                                            except Exception as e:
                                                skipped += 1
                                                logger.debug(f"单图回退嵌入失败: {u}, 错误: {e}")
                                # 全部批次完成后统一保存一次
                                try:
                                    save_faiss_index(faiss_index, username=username, article_id=article_id)
                                except Exception as e:
                                    logger.warning(f"保存FAISS索引失败: {e}")
                                logger.info(f"网页图片批量嵌入完成：批量新增 {batch_added}，回退新增 {fallback_added}，跳过/失败 {skipped}，总计处理 {total}")
                    except Exception as e:
                        logger.error(f"网页图片批量嵌入阶段出错: {e}")
                    # 然后触发DDGS图片补充
                    if username and article_id:
                        faiss_index = create_faiss_index(load_from_disk=True, index_dir='data/faiss', username=username, article_id=article_id)
                        query_for_ddgs = theme or (self.optimized_query or question)
                        logger.info(f"触发DDGS图片补充：query='{query_for_ddgs}', user='{username}', article='{article_id}'")
                        ddgs_added = index_ddgs_images(
                            query=query_for_ddgs,
                            faiss_index=faiss_index,
                            username=username,
                            article_id=article_id,
                            max_results=30,
                            chunk_size=10,
                            log_fn=lambda level, msg: getattr(logger, level if level in ("info","warning","error","debug") else "info")(msg)
                        )
                        if ddgs_added > 0:
                            logger.info(f"DDGS图片补充完成，新增 {ddgs_added} 条。")
                        else:
                            logger.info(f"DDGS图片补充完成，但未新增图片（可能是无搜索结果或反爬虫限制）。")
                except Exception as e:
                    logger.warning(f"DDGS图片补充阶段跳过: {e}（这是正常现象，不影响文章生成）")
            # 返回整合后的结果
            logger.info(f"最终返回搜索结果: {len(search_result)} 条")
            return search_result
        # 如果没有可爬取的URL，也直接返回（仍可由调用方决定是否触发DDGS）
        logger.info(f"最终返回搜索结果: {len(search_result)} 条（无可爬取URL）")
        return search_result

    def auto_writer(self, prompt, outline_summary=''):
        """
        自动生成文章
        :param prompt: 提示词
        :param outline_summary: 大纲
        :return: 生成的文章
        """
        try:
            # 首先根据问题获得搜索结果
            search_result = self.get_search_result(prompt, spider_mode=True)
            if len(search_result) == 0:
                print('No search result!')
                return 0
            if outline_summary == '':
                # 根据抓取的每一篇文章生成大纲
                # 使用线程池并发处理结果
                outlines = llm_task(search_result, prompt, prompt_template.ARTICLE_OUTLINE_GEN)
                # 融合多份大纲
                outline_summary = chat(f'<topic>{prompt}</topic> <content>{outlines}</content>', prompt_template.ARTICLE_OUTLINE_SUMMARY)
            
            # 解析大纲JSON
            outline_summary_json = parse_outline_json(outline_summary, prompt)
            
            repeat_num = len(outline_summary_json['content_outline'])
            # 开始写文章
            article_title = outline_summary_json['title']
            article_summary = outline_summary_json['summary']
            # article_outline = chat(str(outline_summary_json['content_outline']), prompt_template.OUTLINE_MD)
            # 根据大纲一步一步生成文章
            output_path = os.path.join(base_path, 'output', f'{article_title}.md')
            with open(output_path, 'w', encoding='utf-8') as f:
                # f.write(f'# {article_title}\n\n>{article_summary}\n\n[toc]\n\n## 目录：\n{article_outline}\n\n')
                f.write(f'# {article_title}\n\r\n')
                n = 0
                for outline_block in outline_summary_json['content_outline']:
                    n += 1
                    h1 = outline_block['h1']
                    h2 = outline_block['h2']
                    print(f'{h1} {n}/{repeat_num}')
                    
                    if n == 1:
                        # 第一章不要包含h1和h2标题
                        # 根据抓取的内容资料生成内容
                        task = h1 + '之' + h2[0]  # 只取第一个h2
                        question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {task} <<<，注意不要包含任何标题，直接开始正文内容'
                        outline_block_content = llm_task(search_result, question=question, output_type=prompt_template.ARTICLE_OUTLINE_BLOCK)
                        outline_block_content_final = chat(f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{task}，注意不要包含任何标题（不要包含h1和h2标题），直接开始正文内容',
                                           prompt_template.ARTICLE_OUTLINE_BLOCK)
                        print(outline_block_content_final)
                        # 写入文件
                        f.write(outline_block_content_final + '\n\n\r')
                        
                        # 处理第一章的其余h2（如果有）
                        for j in h2[1:]:
                            task = h1 + '之' + j
                            question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {task} <<<'
                            outline_block_content = llm_task(search_result, question=question, output_type=prompt_template.ARTICLE_OUTLINE_BLOCK)
                            outline_block_content_final = chat(f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{task}',
                                               prompt_template.ARTICLE_OUTLINE_BLOCK)
                            print(outline_block_content_final)
                            # 写入文件
                            f.write(outline_block_content_final + '\n\n\r')
                    else:
                        for j in h2:
                            # 根据抓取的内容资料生成内容
                            task = h1 + '之' + j
                            question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {task} <<<'
                            outline_block_content = llm_task(search_result, question=question, output_type=prompt_template.ARTICLE_OUTLINE_BLOCK)
                            outline_block_content_final = chat(f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{task}',
                                               prompt_template.ARTICLE_OUTLINE_BLOCK)
                            print(outline_block_content_final)
                            # 写入文件
                            f.write(outline_block_content_final + '\n\n\r')
            return output_path
        except ConnectionError as e:
            # 捕获连接错误并重新抛出，以便上层处理
            print(f"LLM模型连接失败: {str(e)}")
            raise

def try_load(s: str):
    """
    安全加载JSON字符串：
    - 首选 json.loads
    - 失败后执行常见清洗：单引号->双引号、移除尾随逗号、移除控制字符
    - 尝试修复 content_outline 末尾缺失的 ] 或整体缺失的 }
    - 回退到 ast.literal_eval 以处理类JSON
    - 仍失败则抛出带上下文的信息化异常，交由上层处理。
    """
    # 第一次直接尝试标准JSON
    try:
        return json.loads(s)
    except Exception:
        pass

    # 常见清洗与修复
    import re as _re
    cleaned = s.replace("'", '"')
    # 替换中文引号为英文引号（防止JSON解析失败）
    cleaned = cleaned.replace('"', '"').replace('"', '"')
    cleaned = _re.sub(r",\s*([}\]])", r"\1", cleaned)  # 移除 ,] 或 ,}
    cleaned = _re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", cleaned)  # 控制字符

    # 处理中文/字母/数字之间未转义的双引号，如 从"能用"到"好用"，避免破坏JSON字符串
    # 仅在引号两侧是中日韩字符或字母数字时进行转义，尽量避免影响键名等结构
    try:
        cleaned = _re.sub(r'(?<=[\u4e00-\u9fffA-Za-z0-9])\"(?=[\u4e00-\u9fffA-Za-z0-9])', r'\\"', cleaned)
    except Exception:
        pass

    # content_outline 尾部修补
    try:
        co_key = '"content_outline"'
        co_pos = cleaned.find(co_key)
        if co_pos != -1:
            arr_start = cleaned.find('[', co_pos)
            if arr_start != -1:
                # 仅针对 content_outline 片段进行括号配对检查
                # 在 content_outline 之后、外层对象结束 '}' 之前寻找匹配的 ']'
                outer_obj_end = cleaned.find('}', arr_start)
                if outer_obj_end == -1:
                    outer_obj_end = len(cleaned)
                segment = cleaned[arr_start:outer_obj_end]

                # 计算方括号是否配对完整
                depth = 0
                has_close = False
                for ch in segment:
                    if ch == '[':
                        depth += 1
                    elif ch == ']':
                        depth -= 1
                        if depth == 0:
                            has_close = True
                            break
                # 如果未找到与起始 '[' 配对的 ']'，则在外层对象结束前补一个
                if not has_close:
                    cleaned = cleaned[:outer_obj_end] + ']' + cleaned[outer_obj_end:]
    except Exception:
        pass

    # 第二次尝试标准JSON
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 回退到 Python 字面量
    try:
        import ast
        obj = ast.literal_eval(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 仍失败则抛出，便于上层回退逻辑处理
    preview = cleaned if len(cleaned) <= 300 else cleaned[:300] + "..."
    raise ValueError(f"Failed to parse outline JSON after cleanup. Preview: {preview}")

def parse_outline_json(outline_summary, prompt):
    """
    解析大纲JSON字符串，处理可能的格式错误并提供回退机制
    :param outline_summary: 大纲JSON字符串
    :param prompt: 原始提示词，用于创建默认大纲
    :return: 解析后的大纲JSON对象
    """
    # 首先检查输入是否为空
    if not outline_summary or outline_summary.strip() == "":
        print("警告: 大纲内容为空，使用默认大纲")
        return create_default_outline(prompt)
    
    try:
        # 清理JSON字符串，移除可能导致解析错误的内容
        cleaned_json = outline_summary
        # 移除markdown代码块标记
        cleaned_json = cleaned_json.replace('```json', '').replace('```', '')
        # 移除换行符和多余的空格
        cleaned_json = cleaned_json.strip()
        
        # 尝试找到JSON的开始和结束位置
        start_idx = cleaned_json.find('{')
        end_idx = cleaned_json.rfind('}') + 1
        
        if start_idx < 0 or end_idx <= start_idx:
            print("警告: 无法找到有效的JSON结构，使用默认大纲")
            return create_default_outline(prompt)
            
        cleaned_json = cleaned_json[start_idx:end_idx]
        outline_summary_json = try_load(cleaned_json)

        # 验证JSON结构是否包含必要的字段
        if not validate_outline_structure(outline_summary_json):
            print("警告: JSON结构不完整，使用默认大纲")
            return create_default_outline(prompt)
        return outline_summary_json
    except Exception as e:
        print(f"JSON解析错误: {e}")
        print(f"原始JSON内容: {outline_summary}")
        return create_default_outline(prompt)

def create_default_outline(prompt):
    """
    创建默认的大纲结构
    :param prompt: 原始提示词
    :return: 默认大纲JSON对象
    """
    return {
        "title": prompt,
        "summary": f"关于{prompt}的文章",
        "content_outline": [
            {
                "h1": "1. 引言",
                "h2": ["1.1 背景介绍", "1.2 主要内容概述"]
            },
            {
                "h1": "2. 主要内容",
                "h2": ["2.1 详细说明", "2.2 关键点分析"]
            },
            {
                "h1": "3. 总结",
                "h2": ["3.1 结论", "3.2 展望"]
            }
        ]
    }

def validate_outline_structure(outline_json):
    """
    验证大纲JSON结构是否完整
    :param outline_json: 大纲JSON对象
    :return: 是否有效
    """
    # 检查必要的字段是否存在
    if not isinstance(outline_json, dict):
        return False
        
    required_fields = ["title", "summary", "content_outline"]
    for field in required_fields:
        if field not in outline_json:
            return False
    
    # 检查content_outline是否为列表且不为空
    if not isinstance(outline_json["content_outline"], list) or len(outline_json["content_outline"]) == 0:
        return False
    
    # 检查每个大纲项是否包含h1和h2字段
    for item in outline_json["content_outline"]:
        if not isinstance(item, dict) or "h1" not in item or "h2" not in item:
            return False
        if not isinstance(item["h2"], list):
            return False
    
    return True

def auto_run(topic, outline_summary='', search_result_num=15, type=0, output_type=prompt_template.ARTICLE):
    if type == 0:
        try:
            search = Search(search_result_num)
            return search.auto_writer(topic, outline_summary)
        except ConnectionError as e:
            # 捕获连接错误并重新抛出，以便上层处理
            print(f"LLM模型连接失败: {str(e)}")
            raise
    else:
        try:
            return Search(search_result_num).run(topic, output_type, return_type='search_spider_summary')
        except ConnectionError as e:
            # 捕获连接错误并重新抛出，以便上层处理
            print(f"LLM模型连接失败: {str(e)}")
            raise

if __name__ == '__main__':
    topic = """
    llamafactory训练微调llama3.1详细教程步骤
    """
    outline_summary = ''
    # 使用默认抓取数量，避免未定义变量
    auto_run(topic, search_result_num=DEFAULT_SPIDER_NUM, type=1, output_type=prompt_template.IT_QUERY, outline_summary=outline_summary)