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
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 禁用SSL警告
urllib3.disable_warnings()

# 本地导入
from settings import base_path, LLM_MODEL
from grab_html_content import get_main_content
from llm_chat import chat
import prompt_template
from . import sougou_search
from utils.embedding_utils import Embedding

max_workers = 20
search_result_num = 30

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
    if len(content) < 20000:
        html_content = content
    else:
        html_content = content[:20000]
    # 创建对话提示
    # 这里不捕获异常，让它向上传播
    logger.info(f"处理任务: 模型={model_type}/{model_name}, 内容长度={len(html_content)}")
    chat_result = chat(f'## 参考的上下文资料：<content>{html_content}</content> ## 请严格依据topic完成相关任务：<topic>{question}</topic> ', output_type, model_type, model_name)
    logger.info(f"任务完成: 结果长度={len(chat_result)}")
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
    
    MAX_CONTENT_LENGTH = 20000
    optimized_search_result = []
    current_chunk = ""
    current_titles = []
    
    sorted_results = sorted(search_result, key=lambda x: len(x.get('html_content', ''))) 
    
    for item in sorted_results:
        content = item.get('html_content', '')
        title = item.get('title', 'Untitled')
        
        if len(content) >= MAX_CONTENT_LENGTH:
            optimized_search_result.append({'title': title, 'html_content': content[:MAX_CONTENT_LENGTH], 'url': item.get('url', '')})
            continue
        
        if len(current_chunk) + len(content) > MAX_CONTENT_LENGTH:
            if current_chunk:
                optimized_search_result.append({'title': ' | '.join(current_titles), 'html_content': current_chunk, 'url': 'combined'})
            current_chunk = content
            current_titles = [title]
        else:
            if current_chunk:
                current_chunk += "\n\n---\n\n"
            current_chunk += content
            current_titles.append(title)
    
    if current_chunk:
        optimized_search_result.append({'title': ' | '.join(current_titles), 'html_content': current_chunk, 'url': 'combined'})
    
    logger.info(f"搜索结果优化: 原始数量={len(search_result)}, 优化后数量={len(optimized_search_result)}")
    
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
        if len(outlines) > 25000:
            logger.info(f"结果过长({len(outlines)}字符)，截断至25000字符")
            outlines = outlines[:25000]
        return outlines

class Search:
    def __init__(self, result_num=5):
        """
        初始化搜索引擎类，设置默认结果数量
        :param result_num: 搜索结果数量，默认为8
        """
        self.search_url = "HTTP://searxng.sevnday.top"  # 搜索引擎URL
        self.result_num = result_num  # 结果数量
        self.search_query = ""

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
            normalized_url = sougou_search.normalize_url(url)
            url_hash = sougou_search.calculate_url_hash(url)
            
            # 不再检查全局已处理URL，确保每次搜索都是独立的
            # 原全局去重逻辑已移除，避免跨用户和跨任务的数据污染
                
            # Skip if URL has been processed in this batch
            is_duplicate = False
            for processed_url in processed_urls:
                if sougou_search.is_similar_url(normalized_url, processed_url):
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
        
    def query_search(self, question: str):
        """
        发送请求到搜索引擎，获取JSON响应
        :param question: 查询问题
        :return: JSON数据
        """
        # 使用LLM优化查询问题，专门针对搜索引擎进行优化
        try:
            # 使用格式化字符串正确插入时间
            current_time = time.strftime("%H:%M:%S", time.localtime())
            
            print(f"\原始查询: {question}")
            self.search_query = question
        except Exception as e:
            print(f"LLM查询优化失败: {e}")
            self.search_query = question
            
        # 发送请求到SearXNG搜索引擎
        params = {
            "q": self.search_query,
            "format": "json",
            "pageno": 1,
            "engines": ','.join(["google", "bing", "duckduckgo", "yahoo", "qwant"]),  # 减少搜索引擎数量，提高相关性
            "time_range": "",  # 不限制时间范围
            "safesearch": 0,  # 关闭安全搜索
            "categories": "general",  # 只搜索一般类别
        }
        try:
            response = requests.get(self.search_url, params=params, verify=False)
            data = response.json()
            
            # 同时获取搜狗搜索结果
            try:
                sogou_results = sougou_search.query_search(self.search_query)
                print(f"搜狗搜索返回 {len(sogou_results)} 条结果")
                
                # 将搜狗结果转换为与SearXNG相同的格式并添加到结果中
                if sogou_results and isinstance(sogou_results, list) and len(sogou_results) > 0:
                    # 确保数据中有results字段
                    if 'results' not in data:
                        data['results'] = []
                    
                    # 只取10条搜狗结果
                    sogou_count = 0
                    embedding = Embedding()
                    
                    # 存储搜狗结果及其相似度分数
                    scored_sogou_results = []
                    
                    for result in sogou_results[:10]:
                        # 检查是否是字典格式并包含标题和URL
                        if isinstance(result, dict) and 'title' in result and 'url' in result:
                            title = result['title']
                            url = result['url']
                            
                            # 计算标题与查询词的相似度
                            try:
                                similarity = embedding.cosine_similarity(title, self.search_query)
                                
                                # 将结果与相似度分数一起存储
                                scored_sogou_results.append((result, similarity))
                                print(f"Sogou result: {title[:30]}... - 相似度: {similarity:.4f}")
                            except Exception as e:
                                print(f"Error calculating similarity for sogou result: {str(e)}")
                    
                    # 按相似度降序排序
                    scored_sogou_results.sort(key=lambda x: x[1], reverse=True)
                    
                    # 收集所有相似度分数以便分析
                    all_scores = [score for _, score in scored_sogou_results]
                    if all_scores:
                        min_score = min(all_scores)
                        max_score = max(all_scores)
                        avg_score = sum(all_scores) / len(all_scores)
                        print(f"搜狗结果相似度统计: 最小={min_score:.4f}, 最大={max_score:.4f}, 平均={avg_score:.4f}")
                        
                        # 使用标准阈值，因为相似度分数实际上很好
                        SIMILARITY_THRESHOLD = 0.1  # 相似度阈值
                        filtered_results = [(result, score) for result, score in scored_sogou_results if score >= SIMILARITY_THRESHOLD]
                        
                        print(f"搜狗结果相似度过滤: {len(filtered_results)}/{len(scored_sogou_results)} 结果通过阈值 {SIMILARITY_THRESHOLD}")
                    
                    # 处理过滤后的搜狗结果
                    for result, similarity in filtered_results:
                        title = result['title']
                        url = result['url']
                        
                        # 确保URL是完整的并且有效
                        if not url:
                            print(f"跳过无效URL的搜狗结果: {title[:30]}...")
                            continue
                            
                        if not url.startswith(('http://', 'https://')):
                            # 如果是相对路径，添加域名
                            if url.startswith('/'):
                                url = 'https://weixin.sogou.com' + url
                            else:
                                url = 'https://' + url
                            print(f"修正URL: {url}")
                        
                        data['results'].append({
                            'title': title,
                            'url': url,  # 使用实际的URL，允许重定向
                            'content': f"Sogou Search Result: {title}",
                            'score': similarity,  # 使用计算出的相似度作为分数
                            'engine': 'sogou',
                            'sogou_result': True  # 标记为搜狗结果，方便后续处理
                        })
                        sogou_count += 1
                        print(f"添加搜狗结果: {title[:30]}... - URL: {url}")
                    
                    print(f"成功添加 {sogou_count} 条搜狗搜索结果 (相似度阈值: {SIMILARITY_THRESHOLD}), 总计{len(data['results'])}条结果")
                    
                    # 如果没有添加任何搜狗结果，检查可能的原因
                    if sogou_count == 0 and len(filtered_results) > 0:
                        print("警告: 有符合相似度阈值的搜狗结果，但没有被添加。可能是URL格式问题或其他条件限制。")
                        for result, similarity in filtered_results[:3]:  # 只打印前3个作为示例
                            title = result.get('title', 'No Title')
                            url = result.get('url', 'No URL')
                            print(f"未添加的结果示例: {title[:30]}... - URL: {url} - 相似度: {similarity:.4f}")
            except Exception as e:
                print(f"搜狗搜索失败: {e}")
                
            return data
        except Exception as e:
            print(f"SearXNG搜索失败: {e}")
            return None

    def get_search_result(self, question: str, is_multimodal=False, theme="", spider_mode=False, progress_callback: Optional[callable] = None, username: str = None, article_id: str = None):
        data = self.query_search(question)
        search_result = []
        search_engine_urls = []
        
        # 检查是否有搜索结果
        if data and data.get('results'):
            # 添加搜索引擎的结果
            search_engine_items = []
            for item in data['results']:
                # 检查是否有URL
                if 'url' in item:
                    search_engine_urls.append(item['url'])
                    search_engine_items.append({
                        'title': item.get('title', ''),
                        'url': item['url'],
                        'html_content': '',
                    })
            
            # Deduplicate search engine results
            search_engine_items = self.deduplicate_urls(search_engine_items)
            search_result.extend(search_engine_items)
            logger.info(f"Added {len(search_engine_items)} deduplicated search engine results")
            
            # 添加搜狗搜索的结果（已在sougou_search模块中进行了初步去重）
            sougou_result = sougou_search.query_search(question)
            if sougou_result:
                sougou_items = []
                for item in sougou_result:
                    if item['url'] not in search_engine_urls:
                        search_engine_urls.append(item['url'])
                        sougou_items.append({
                            'title': item.get('title', ''),
                            'url': item['url'],
                            'html_content': '',
                        })
                
                # Deduplicate Sogou results against global processed URLs
                sougou_items = self.deduplicate_urls(sougou_items)
                search_result.extend(sougou_items)
                logger.info(f"Added {len(sougou_items)} deduplicated Sogou search results")
                    
            # Deduplicate search engine results
            search_engine_items = self.deduplicate_urls(search_engine_items)
            search_result.extend(search_engine_items)
            
            # 从原始查询文本中提取关键词，用于相关性过滤
            original_keywords = set(re.findall(r'\w+', question))
            optimized_keywords = set(re.findall(r'\w+', self.search_query))
            important_keywords = original_keywords.union(optimized_keywords)
            
            # 将结果按相关性评分排序
            scored_results = []
            for i in data['results']:
                # 跳过特定文件类型和低分结果
                if i['url'].split('.')[-1] in ['xlsx', 'pdf', 'doc', 'docx', 'xls', 'ppt', 'pptx']:
                    continue
                if i['score'] < 0.15:
                    continue
                    
                # 计算关键词匹配度
                title_keywords = set(re.findall(r'\w+', i.get('title', '').lower()))
                content_keywords = set(re.findall(r'\w+', i.get('content', '').lower()))
                
                # 获取标题和内容中与查询关键词的重叠数
                title_match = len(title_keywords.intersection(important_keywords))
                content_match = len(content_keywords.intersection(important_keywords))
                
                # 基于原始分数和关键词匹配度的综合分数
                relevance_score = (i['score'] * 0.4) + (title_match * 0.4) + (content_match * 0.2)
                    
                scored_results.append((i, relevance_score))
                
            # 按相关性分数降序排序
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # 提取排序后的结果
            for i, score in scored_results:
                url_display = i['url'][:37] + '...' if len(i['url']) > 40 else i['url']
                print(f"{url_display} - 相关度: {score:.2f} - {i['title']}")
                search_result.append({
                    'title': i['title'], 
                    'url': i['url'], 
                    'html_content': i['content'] if 'content' in i else '',
                    'relevance_score': score
                })
                search_engine_urls.append(i['url'])
            # 获取网页主要内容 - 始终爬取所有URL
            if len(search_engine_urls) > 0:
                # 在爬取内容前，确保所有URL都已去重
                final_urls = []
                final_url_map = {}
                
                # 构建最终去重的URL列表
                for item in search_result:
                    url = item['url']
                    normalized_url = sougou_search.normalize_url(url)
                    
                    # 如果URL还未被处理，添加到最终列表
                    if normalized_url not in final_url_map:
                        final_urls.append(url)
                        final_url_map[normalized_url] = url
                
                logger.info(f"Final deduplicated URLs for content grabbing: {len(final_urls)}")
                
                # 爬取内容
                result, task_id = asyncio.run(get_main_content(final_urls, is_multimodal=is_multimodal, theme=theme, progress_callback=progress_callback, username=username, article_id=article_id))
                
                # 创建字典，存储爬取到的内容和图片
                html_content_dict = {}
                image_dict = {}  # 存储每个URL对应的图片
                
                # 处理爬取结果，将内容和图片映射到URL
                for item in result:
                    content = item.get('content', '').replace('\n', '').replace(' ', '')
                    url = item.get('url', '')
                    original_url = item.get('original_url', url)
                    images = item.get('images', [])
                    
                    # 存储内容和图片
                    if content:
                        html_content_dict[url] = content
                        if original_url != url:
                            html_content_dict[original_url] = content
                    
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
                        logger.debug(f"Added content for URL: {url}")
                    else:
                        # 尝试匹配部分URL
                        matched = False
                        for crawled_url in html_content_dict.keys():
                            # 检查URL是否为子字符串或域名匹配
                            if url in crawled_url or crawled_url in url or \
                               urlparse(url).netloc == urlparse(crawled_url).netloc:
                                item['html_content'] += html_content_dict[crawled_url]
                                logger.info(f"Found partial match for content: {url} -> {crawled_url}")
                                matched = True
                                break
                        if not matched:
                            logger.warning(f"No content found for URL: {url}")
                    
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
                                matched = True
                                break
                        
                        if not matched and url not in image_dict:
                            logger.debug(f"No images found for URL: {url}")
            return search_result
        else:
            return None

    def run(self, question, output_type=prompt_template.ARTICLE, return_type='search'):
        """
        主函数，负责整个程序的流程
        return_type:
            search 返回搜索引擎的结果
            search_spider 返回搜索后并爬取页面的内容的结果
            search_spider_summary 返回搜索-爬取-总结后的结果
        """
        print('搜索中......')
        # 创建Search实例并获取搜索结果
        if return_type == 'search':
            return self.get_search_result(question)
        # 获取搜索结果
        # 中文查询
        search_result = self.get_search_result(question, is_multimodal=False, theme=question)
        print('抓取完成开始形成摘要......')
        # 使用线程池并发处理结果
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_result, i['html_content'], question, output_type) for i in search_result]
        # 收集并合并结果
        lock = threading.Lock()
        combine_contents = ""
        for future in concurrent.futures.as_completed(futures):
            with lock:
                combine_contents += future.result()
        if return_type == 'search_spider':
            return combine_contents
        print('汇总中......')
        if return_type == 'search_spider_summary':
            # 生成最终结果
            result = chat(f'<topic>{question}</topic> <content>{combine_contents}</content>',
                                prompt_template.ARTICLE_FINAL)
            print(result)
            return result

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
                        question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {task} <<<，注意不要包含任何标题，直接开始正文内容',
                        outline_block_content = llm_task(search_result, question=question, output_type=prompt_template.ARTICLE_OUTLINE_BLOCK)
                        outline_block_content_final = chat(f'<完整大纲>{outline_summary}</完整大纲> <相关资料>{outline_block_content}</相关资料> 请根据上述信息，书写大纲中的以下这部分内容：{task}，注意不要包含任何标题（不要包含h1和h2标题），直接开始正文内容',
                                           prompt_template.ARTICLE_OUTLINE_BLOCK)
                        print(outline_block_content_final)
                        # 写入文件
                        f.write(outline_block_content_final + '\n\n\r')
                        
                        # 处理第一章的其余h2（如果有）
                        for j in h2[1:]:
                            task = h1 + '之' + j
                            question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {task} <<<',
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
                            question = f'<完整大纲>{outline_summary}</完整大纲> 请根据上述信息，书写出以下内容 >>> {task} <<<',
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
        
        # 尝试解析JSON
        try:
            outline_summary_json = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            print(f"初次解析JSON失败: {e}")
            # 尝试修复常见的JSON错误
            # 1. 处理可能的尾部逗号问题
            cleaned_json = cleaned_json.replace(',}', '}').replace(',\n}', '}').replace(',\r\n}', '}')
            # 2. 处理引号不匹配的问题
            cleaned_json = cleaned_json.replace('"h2": [', '"h2": [')
            cleaned_json = cleaned_json.replace(']"', ']')
            # 3. 处理可能的Unicode转义问题
            cleaned_json = cleaned_json.encode().decode('unicode_escape')
            
            # 再次尝试解析
            outline_summary_json = json.loads(cleaned_json)
        
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
    auto_run(topic, search_result_num=search_result_num, type=1, output_type=prompt_template.IT_QUERY, outline_summary=outline_summary)