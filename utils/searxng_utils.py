import json

import requests
import urllib3
urllib3.disable_warnings()
from grab_html_content import get_main_content
from llm_chat import chat
import asyncio
import prompt_template

class Search:
    def __init__(self, result_num=15):
        self.search_url = "HTTP://searxng.sevnday.top"
        self.result_num = result_num
        self.llm_chat_system_prompt = """
        任务描述：
        请对我输入的文章内容进行内容提炼和梳理，确保保留与主题紧密相关的关键部分。具体要求如下：
        保留与主题相符的关键信息，包括但不限于：
        文章的中心思想或主要论点。
        任何数字相关的参数指标，如统计数据、百分比、时间、金额等。
        重要的事实、发现或结论。
        去除文章中的冗余信息、次要细节或与主题不直接相关的部分。
        确保最终提炼的内容长度不超过1000字。
        保持内容的连贯性和逻辑性，使读者能够清晰理解文章的核心内容。
        请根据上述要求，对文章内容进行提炼和梳理。
        如果内容是乱码或者全是符号则直接返回0。
        """

    def query_search(self, question: str):
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

    def get_search_result(self, question: str, llm_chat=False):
        data = self.query_search(question)
        print('搜索完成开始抓取网页数据')
        if data:
            url_list = [i['url'] for i in data['results'][:self.result_num] if i['url'].split('.')[-1] not in ['xlsx', 'pdf']
                        and i['score'] > 0.3
                        and 'bbc' not in i['url']]
            html_content_list = asyncio.run(get_main_content(url_list))
            if len(html_content_list) == 0:
                return None
            if llm_chat:
                html_content_list_result = [chat(i, self.llm_chat_system_prompt) for i in html_content_list]
            else:
                html_content_list_result = [i for i in html_content_list if i != '0']
            result = []
            for index, html_content in enumerate(html_content_list_result):
                result.append(
                    {'title': data['results'][index]['title'], 'url': data['results'][index]['url'], 'html_content': html_content}
                )
            return result
        else:
            return None

def main():
    question = '现在中国教育处于那种阶段？为什么出生人口变少，上学却还是很难？'
    get_search_result = Search().get_search_result
    result = get_search_result(question, llm_chat=False)
    chat_prompt = '\n'.join([i['html_content'] for i in result])
    print(len(chat_prompt))
    if len(chat_prompt) > 20000:
        chat_prompt = f'将content作为你的知识 <content>{chat_prompt[:20000]}</content> query:{question} '
    print(chat(chat_prompt, prompt_template.ARTICLE))

if __name__ == '__main__':
    main()