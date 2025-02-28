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
import hashlib
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

async def download_image(session: aiohttp.ClientSession, img_src: str, image_hash_cache: dict, task_id: str) -> str:
    """
    异步下载图片，使用MD5哈希确保每张图片只下载一次
    """
    if img_src in image_hash_cache:
        logger.info(f"Image URL already processed: {img_src}, using cached path: {image_hash_cache[img_src]}")
        return image_hash_cache[img_src]
    
    try:
        async with session.get(img_src, ssl=False) as response:
            if response.status != 200:
                logger.warning(f"Failed to download image {img_src}, status: {response.status}")
                return ''
                
            content = await response.read()
            content_size = len(content)
            
            if content_size < MIN_IMAGE_SIZE:
                logger.info(f"Image {img_src} is too small ({content_size} bytes), skipping")
                image_hash_cache[img_src] = ''
                return ''
            
            # 计算图片内容的MD5哈希值
            content_hash = hashlib.md5(content).hexdigest()
            
            # 检查是否已经下载过相同内容的图片
            for cached_url, cached_path in image_hash_cache.items():
                if cached_url != img_src and cached_path.startswith(str(IMAGES_DIR / task_id)) and Path(cached_path).exists():
                    try:
                        with open(cached_path, 'rb') as f:
                            cached_content = f.read()
                            cached_hash = hashlib.md5(cached_content).hexdigest()
                            if cached_hash == content_hash:
                                logger.info(f"Duplicate image content detected. Using existing file: {cached_path}")
                                image_hash_cache[img_src] = cached_path
                                return cached_path
                    except Exception as e:
                        logger.warning(f"Error checking cached file {cached_path}: {str(e)}")
            
            # 检查图片尺寸
            try:
                img = Image.open(BytesIO(content))
                width, height = img.size
                
                # 跳过 480x480 和 226x226 尺寸的图片
                if (width == 480 and height == 480) or (width == 226 and height == 226) or (width == 300 and height == 300) or (width == 656 and height == 656):
                    logger.info(f"Skipping image with dimensions {width}x{height}: {img_src}")
                    image_hash_cache[img_src] = ''
                    return ''
            except Exception as e:
                logger.warning(f"Failed to check image dimensions for {img_src}: {str(e)}")
                
            # 使用MD5哈希值作为文件名的一部分，确保唯一性
            original_filename = Path(img_src).name
            extension = ''.join(Path(original_filename).suffixes)
            if not any(extension.lower().endswith(ext) for ext in VALID_IMAGE_EXTENSIONS):
                extension = '.jpg'
                
            file_name = f"{content_hash}{extension}"
                
            # Create task-specific folder
            task_folder = IMAGES_DIR / task_id
            task_folder.mkdir(exist_ok=True)
            file_path = task_folder / file_name
            
            # 检查文件是否已存在（基于哈希值的文件名）
            if file_path.exists():
                logger.info(f"File with same hash already exists: {file_path}")
                image_hash_cache[img_src] = str(file_path)
                return str(file_path)
            
            # 保存图片 - 使用同步文件操作
            with open(file_path, 'wb') as f:
                f.write(content)
                
            image_hash_cache[img_src] = str(file_path)
            logger.info(f"Successfully downloaded image: {file_path}")
            return str(file_path)
            
    except Exception as e:
        logger.error(f"Error downloading image {img_src}: {str(e)}")
        image_hash_cache[img_src] = ''
        return ''

async def text_from_html(body: str, session: aiohttp.ClientSession, task_id: str) -> Dict[str, any]:
    """
    从HTML内容中提取文本和图片
    """
    try:
        soup = BeautifulSoup(body, 'html.parser')
        texts = soup.findAll(text=True)
        visible_texts = filter(tag_visible, texts)
        
        # 提取正文文本
        text_content = " ".join(t.strip() for t in visible_texts if t.strip())
        
        # 提取图片
        img_tags = soup.find_all('img')
        img_paths = []
        
        if img_tags:
            # 创建一个字典来存储图片哈希和路径
            image_hash_cache = {}
            
            # 创建异步任务列表
            img_tasks = []
            for img in img_tags:
                img_src = img.get('src', '')
                if img_src and not img_src.startswith('data:'):
                    img_tasks.append(download_image(session, img_src, image_hash_cache, task_id))
            
            # 等待所有图片下载完成
            img_paths = await asyncio.gather(*img_tasks)
            img_paths = [path for path in img_paths if path]  # 过滤空路径
        
        return {
            'text': text_content,
            'images': img_paths
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