# 导入所需的库
# 将当前目录加入环境变量
import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from settings import base_path, LLM_MODEL
import json
import requests
import urllib3
urllib3.disable_warnings()  # 禁用SSL警告
from grab_html_content import get_main_content # 用于获取网页主要内容的函数
from llm_chat import chat  # 对话生成函数
import asyncio
import prompt_template  # 提示模板模块
import concurrent.futures  # 并发执行任务
import threading  # 多线程

max_workers = 20
search_result_num = 30

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
    chat_result = chat(f'## 参考的上下文资料：<content>{html_content}</content> ## 请严格依据topic完成相关任务：<topic>{question}</topic> ', output_type, model_type, model_name)
    # print(f'总结后的字数统计：{len(chat_result)}')
    return chat_result


def llm_task(search_result, question, output_type, model_type, model_name, max_workers=20):
    """
    使用线程池并发处理搜索结果
    :param search_result: 搜索结果列表
    :param question: 查询问题
    :param output_type: 输出类型
    :param model_type: 模型类型
    :param model_name: 模型名称
    :param max_workers: 最大线程数
    :return: 处理后的结果
    """
    if model_type == 'glm':
        max_workers = 10
        
    # 创建一个线程安全的标志，用于标记是否发生了连接错误
    connection_error = None
    
    # 定义一个包装函数来捕获ConnectionError
    def process_result_wrapper(content, question, output_type, model_type, model_name):
        nonlocal connection_error
        try:
            return process_result(content, question, output_type, model_type, model_name)
        except ConnectionError as e:
            connection_error = e
            # 返回一个占位符，这个结果不会被使用
            return "CONNECTION_ERROR"
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_result_wrapper, i['html_content'], question, output_type, model_type, model_name) for i in search_result]
        
        # 等待所有任务完成
        concurrent.futures.wait(futures)
        
        # 检查是否有连接错误
        if connection_error:
            raise connection_error
    
    if output_type == prompt_template.ARTICLE_OUTLINE_GEN:
        # 获取结果
        outlines = '\n'.join([future.result().replace('\n', '').replace('```json', '').replace('```', '') for future in
                              concurrent.futures.as_completed(futures)])
    else:
        # 获取结果
        outlines = '\n'.join([future.result() for future in concurrent.futures.as_completed(futures)])
    
    if len(outlines) > 25000:
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

    def query_search(self, question: str):
        """
        发送请求到搜索引擎，获取JSON响应
        :param question: 查询问题
        :return: JSON数据
        """
        # 优化询问的问题
        # question = chat(question, "根据我的问题重新整理格式并梳理成搜索引擎的查询问题，要求保留原文语意。使用中文。")
        url = self.search_url
        params = {
            "q": question,
            "format": "json",
            "pageno": 1,
            "engines": ','.join(["google", "bing", "yahoo", "duckduckgo", "qwant"]),
            # "categories_exclude": "social",
            # "categories_include": "general",
            # "categories_include_exclude": "include",
            # "categories_exclude_exclude": "exclude",
            # "categories_include_exclude_exclude": "exclude",
        }
        try:
            response = requests.get(url, params=params, verify=False)
            data = response.json()
            return data
        except Exception as e:
            print(e)
            return None

    def get_search_result(self, question: str, spider_mode=False):
        """
        根据问题获取搜索结果
        :param question: 查询问题
        :return: 搜索结果列表
        """
        data = self.query_search(question)
        if data:
            # 过滤并提取合适的搜索结果URL
            search_result = []
            search_engine_urls = []
            for i in data['results'][:self.result_num]:
                if i['url'].split('.')[-1] not in ['xlsx', 'pdf'] and 'bbc' not in i['url'] and i['score'] > 0.1:
                    search_result.append(
                        {'title': i['title'], 'url': i['url'], 'html_content': i['content'] if 'content' in i else ''}
                    )
                    search_engine_urls.append(i['url'])
                    print(i['url'], i['score'], i['title'])
            if spider_mode:
                # 获取网页主要内容
                if len(search_engine_urls) > 0:
                    result = asyncio.run(get_main_content(search_engine_urls))
                    html_content_dict = {i['url']: i['content'].replace('\n', '').replace(' ', '') for i in result}
                    # 构建结果列表
                    for i in search_result:
                        i['html_content'] += html_content_dict[i['url']]
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
        # 爬取搜索结果 中英结合
        # 中文查询
        search_result = self.get_search_result(question, spider_mode=True)
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