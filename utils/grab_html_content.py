import os
# 将本文件上一级目录作为主目录
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from bs4.element import Comment
from playwright.async_api import async_playwright
from io import BytesIO
from PIL import Image
import uuid
import random
import re
from typing import List, Dict
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量配置
MIN_IMAGE_SIZE = 50 * 1024  # 50KB
VALID_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
IMAGES_DIR = Path('images')
IMAGES_DIR.mkdir(exist_ok=True)

def tag_visible(element) -> bool:
    """
    判断HTML元素是否应该可见
    """
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]', 'button', 'a']:
        return False
    if isinstance(element, Comment):
        return False
    return True

async def download_image(session: aiohttp.ClientSession, img_src: str, image_url_cache: set, task_id: str) -> str:
    """
    异步下载图片
    """
    if img_src in image_url_cache:
        return ''
    
    try:
        async with session.get(img_src, ssl=False) as response:
            if response.status != 200:
                logger.warning(f"Failed to download image {img_src}, status: {response.status}")
                return ''
                
            content = await response.read()
            content_size = len(content)
            
            if content_size < MIN_IMAGE_SIZE:
                logger.info(f"Image {img_src} is too small ({content_size} bytes), skipping")
                return ''
                
            # 生成文件名
            file_name = f"{uuid.uuid4()}{random.randint(1, 99999)}_{Path(img_src).name}"
            if not any(file_name.lower().endswith(ext) for ext in VALID_IMAGE_EXTENSIONS):
                file_name += '.jpg'
                
            # Create task-specific folder
            task_folder = IMAGES_DIR / task_id
            task_folder.mkdir(exist_ok=True)
            file_path = task_folder / file_name
            
            # 保存图片 - 使用同步文件操作
            with open(file_path, 'wb') as f:
                f.write(content)
                
            image_url_cache.add(img_src)
            logger.info(f"Successfully downloaded image: {file_path}")
            return str(file_path)
            
    except Exception as e:
        logger.error(f"Error downloading image {img_src}: {str(e)}")
        return ''

async def text_from_html(body: str, session: aiohttp.ClientSession, task_id: str) -> Dict[str, any]:
    """
    从HTML内容中提取文本和图片
    """
    try:
        soup = BeautifulSoup(body, 'html.parser')
        texts = soup.findAll(string=True)
        image_url_cache = set()
        
        # 异步下载所有图片
        img_tasks = []
        for img in soup.find_all('img'):
            img_src = img.get('src', '').split('?')[0]
            if img_src and img_src.startswith('http') and not img_src.endswith('.svg'):
                img_tasks.append(download_image(session, img_src, image_url_cache, task_id))
        
        image_paths = await asyncio.gather(*img_tasks)
        image_paths = [path for path in image_paths if path]  # 过滤空路径
        
        # 处理文本
        visible_texts = filter(tag_visible, texts)
        cleaned_text = re.sub(r'\s+', ' ', ' '.join(t.strip() for t in visible_texts)).strip()
        
        return {
            'text': cleaned_text,
            'images': image_paths
        }
        
    except Exception as e:
        logger.error(f"Error processing HTML content: {str(e)}")
        return {'text': '', 'images': []}

async def fetch(browser, url: str, task_id: str) -> Dict[str, any]:
    """
    获取页面内容
    """
    await asyncio.sleep(random.uniform(1, 3))  # 随机延迟，避免被反爬
    
    async with aiohttp.ClientSession() as session:
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
            await page.goto(url, timeout=60000)
            content = await page.content()
            result = await text_from_html(content, session, task_id)
            return {
                'url': url,
                'content': result['text'],
                'images': result['images']
            }
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return {'url': url, 'content': '', 'images': []}
        finally:
            await page.close()
            await context.close()

async def get_main_content(url_list: List[str], task_id: str = None) -> List[Dict[str, any]]:
    """
    获取多个URL的内容
    :param url_list: URL列表
    :param task_id: 任务ID，如果未提供则使用时间戳
    """
    """
    获取多个URL的内容
    """
    async with async_playwright() as p:
        browser = await p.firefox.launch()
        try:
            # 如果没有提供task_id，使用时间戳作为任务ID
            if task_id is None:
                task_id = f"task_{int(asyncio.get_event_loop().time())}"
            
            tasks = [fetch(browser, url, task_id) for url in url_list]
            results = await asyncio.gather(*tasks)
            return results
        finally:
            await browser.close()

if __name__ == '__main__':
    url_list = ['http://news.china.com.cn/2024-11/18/content_117554263.shtml']
    main_content = asyncio.run(get_main_content(url_list, task_id="test_task"))
    if main_content:
        print(main_content)
    else:
        print("Failed to retrieve the main content.")