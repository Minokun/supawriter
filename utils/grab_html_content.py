import asyncio
import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import asyncio
from playwright.async_api import async_playwright
import os

output_folder = '../images'
def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]', 'button', 'a']:
        return False
    if isinstance(element, Comment):
        return False
    return True

def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(string=True)
    visible_texts = filter(tag_visible, texts)
    return ((u" ".join(t.strip() for t in visible_texts).replace(' ', '')
            .replace('\n', '')
            .replace('\r', '')
            .replace('\t', ''))
            .replace('\u200b', ''))

def get_main_content_by_request(url_list):
    try:
        result = []
        for url in url_list:
            response = requests.get(url, timeout=3)
            response.raise_for_status()  # 确保请求成功
            result.append(filter(tag_visible, response.text))
        return result
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

async def fetch(browser, url):
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True,
        accept_downloads=True,
        java_script_enabled=True,
        bypass_csp=True,
        extra_http_headers={'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7'},
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        geolocation={'latitude': 39.9042, 'longitude': 116.4074},
    )
    page = await context.new_page()
    try:
        # 使用 wait_for 来设置超时时间
        await page.goto(url, timeout=60000)
        # images = await page.query_selector_all('img')
        # print(images)
        content = await page.content()
    except Exception as e:
        print(f"Timeout occurred while fetching {url}")
        content = ''
    # finally:
    #     await page.close()
    return {'url': url, 'content': text_from_html(content)}

async def get_main_content(url_list):
    async with async_playwright() as p:
        browser = await p.firefox.launch()
        tasks = []
        for url in url_list:
            tasks.append(fetch(browser, url))
        html_content_list = await asyncio.gather(*tasks)
        await browser.close()
        return html_content_list


if __name__ == '__main__':
    url_list = ['https://news.sina.com.cn/o/2024-05-09/doc-inaurtsc9410350.shtml?tj=cxvertical_pc_hp&tr=181']
    main_content = asyncio.run(get_main_content(url_list))
    if main_content:
        print(len(main_content))
        print(main_content)
    else:
        print("Failed to retrieve the main content.")