# 导入所需的库
# 将当前目录加入环境变量
import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import json
import requests
import urllib3
urllib3.disable_warnings()  # 禁用SSL警告
from grab_html_content import get_main_content  # 用于获取网页主要内容的函数
from llm_chat import chat  # 对话生成函数
import asyncio
import prompt_template  # 提示模板模块
import concurrent.futures  # 并发执行任务
import threading  # 多线程



def process_result(content, question, output_type=prompt_template.ARTICLE):
    """
    处理单个搜索结果，生成摘要
    :param content: 搜索结果字典
    :param question: 查询问题
    :param output_type: 输出类型
    :return: 摘要内容
    """
    print(f'字数统计：{len(content)}')
    if len(content) < 20000:
        html_content = content
    else:
        html_content = content[:20000]
    # 创建对话提示
    chat_result = chat(f'## 参考的上下文知识：<content>{html_content}</content> ## 围绕主题：<topic>{question}</topic> ', output_type)
    print(f'总结后的字数统计：{len(chat_result)}')
    return chat_result

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
                if i['url'].split('.')[-1] not in ['xlsx', 'pdf'] and i['score'] > 0.3 and 'bbc' not in i['url']:
                    search_result.append(
                        {'title': i['title'], 'url': i['url'], 'html_content': i['content']}
                    )
                    search_engine_urls.append(i['url'])
                    print(i['url'], i['score'], i['title'])
            if spider_mode:
                # 获取网页主要内容
                if len(search_engine_urls) > 0:
                    html_content_dict = {i['url']: i['content'] for i in asyncio.run(get_main_content(search_engine_urls))}
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
        result = self.get_search_result(question, spider_mode=True)
        print('抓取完成开始形成摘要......')
        # 使用线程池并发处理结果
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(process_result, i['html_content'], question, output_type) for i in result]
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
            return chat(f'<topic>{question}</topic> <content>{combine_contents}</content>',
                                prompt_template.ARTICLE_FINAL)



if __name__ == '__main__':
    result = Search(result_num=15).run(question='''
    微软最新发布会
    ''', output_type=prompt_template.ARTICLE, return_type='search_spider_summary')
    print(len(result))
    print(result)
