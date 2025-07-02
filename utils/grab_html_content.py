import os
# 将本文件上一级目录作为主目录
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import aiohttp
import hashlib
import logging
import json
from bs4 import BeautifulSoup
from bs4.element import Comment
from playwright.async_api import async_playwright
from pathlib import Path
from io import BytesIO
from PIL import Image
from typing import List, Dict, Set, Union, Optional
import urllib.parse  # 完整导入urllib.parse模块
from utils.image_url_mapper import ImageUrlMapper
import uuid
import random
import re
import hashlib
from typing import List, Dict
from pathlib import Path
from utils.gemma3_client import call_gemma3_api, sample_prompt
from utils.embedding_utils import add_to_faiss_index, create_faiss_index

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FAISS索引实例 - 尝试从磁盘加载
# 这个索引实例将在grab_html_content.py中创建并填充数据，然后保存到磁盘
# auto_write.py中会从磁盘加载已经填充了数据的索引
INDEX_DIR = 'data/faiss'
faiss_index = create_faiss_index(load_from_disk=True, index_dir=INDEX_DIR)
logger.info(f"FAISS index loaded/created in grab_html_content.py with {faiss_index.get_size()} items")

def get_streamlit_faiss_index():
    """获取FAISS索引实例，优先从磁盘加载"""
    global faiss_index, INDEX_DIR
    
    # 如果全局索引为None或为空，尝试从磁盘重新加载
    if faiss_index is None or faiss_index.get_size() == 0:
        faiss_index = create_faiss_index(load_from_disk=True, index_dir=INDEX_DIR)
        logger.info(f"Reloaded FAISS index from disk with {faiss_index.get_size()} items")
        
    return faiss_index

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

async def download_image(session: aiohttp.ClientSession, img_src: str, image_hash_cache: dict, task_id: str, is_multimodal: bool = False, theme: str = "", stats: dict = None) -> Union[str, dict]:
    """
    异步下载图片，使用MD5哈希确保每张图片只下载一次
    
    Args:
        session: aiohttp客户端会话
        img_src: 图片URL
        image_hash_cache: 图片哈希缓存字典
        task_id: 任务ID
        is_multimodal: 是否使用多模态模型处理图片，默认为False
        theme: 主题，用于多模态模型判断图片相关性
        stats: 统计字典，用于记录成功和失败的下载数量
        
    Returns:
        如果is_multimodal为False，返回下载的图片路径字符串
        如果is_multimodal为True，返回包含图片描述和相关性的字典
    """
    # 初始化统计字典（如果未提供）
    if stats is None:
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'cached': 0,
            'skipped': 0
        }
    
    if img_src in image_hash_cache:
        stats['cached'] += 1
        logger.info(f"Using cached image: {img_src}")
        return image_hash_cache[img_src]
    
    try:
        # 设置请求头，模拟浏览器行为
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.163.com/',  # 对于网易图片，添加合适的Referer
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        # 特殊处理网易图片URL
        if 'nimg.ws.126.net' in img_src or '126.net' in img_src:
            logger.info(f"处理网易图片URL: {img_src}")
            # 如果是网易的URL，尝试提取实际图片URL
            if 'url=' in img_src:
                try:
                    # 提取实际的图片URL
                    from urllib.parse import urlparse, parse_qs
                    parsed_url = urlparse(img_src)
                    query_params = parse_qs(parsed_url.query)
                    if 'url' in query_params:
                        actual_img_url = query_params['url'][0]
                        # logger.info(f"提取到实际图片URL: {actual_img_url}")
                        # 使用实际的图片URL替代原始URL
                        img_src = actual_img_url
                except Exception as e:
                    # logger.warning(f"提取网易实际图片URL失败: {str(e)}")
                    pass
        
        async with session.get(img_src, ssl=False, headers=headers) as response:
            if response.status != 200:
                # logger.warning(f"Failed to download image {img_src}, status: {response.status}")
                # 如果是403错误，尝试其他方法
                if response.status == 403:
                    # logger.info(f"尝试使用不同的请求头重新下载图片: {img_src}")
                    # 尝试使用不同的User-Agent和Referer
                    alt_headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
                        'Referer': urllib.parse.urljoin(img_src, '/'),  # 使用图片URL的域名作为Referer
                    }
                    try:
                        async with session.get(img_src, ssl=False, headers=alt_headers) as alt_response:
                            if alt_response.status == 200:
                                response = alt_response
                            else:
                                # logger.warning(f"备用请求头也无法下载图片: {img_src}, 状态码: {alt_response.status}")
                                return '' if not is_multimodal else None
                    except Exception as e:
                        # logger.warning(f"备用请求头下载图片失败: {str(e)}")
                        return '' if not is_multimodal else None
                else:
                    return '' if not is_multimodal else None
                
            content = await response.read()
            content_size = len(content)
            
            # 检查图片大小和尺寸
            def should_skip_image():
                """Helper function to determine if image should be skipped"""
                # 1. 检查文件大小
                if content_size < MIN_IMAGE_SIZE:
                    # logger.info(f"Skipping small file: {img_src} ({content_size/1024:.1f}KB < {MIN_IMAGE_SIZE/1024:.1f}KB)")
                    return True
                    
                # 2. 检查图片尺寸
                try:
                    img = Image.open(BytesIO(content))
                    width, height = img.size
                    
                    # 常见图标尺寸列表
                    ICON_SIZES = {
                        (480, 480), 
                        (226, 226), 
                        (300, 300), 
                        (656, 656)
                    }
                    
                    # 检查是否为常见图标尺寸
                    if (width, height) in ICON_SIZES:
                        logger.info(f"Skipping common icon size: {img_src} ({width}x{height})")
                        return True
                        
                    # 检查是否为小图片
                    if width < 200 and height < 200:
                        logger.info(f"Skipping small image: {img_src} ({width}x{height})")
                        return True
                        
                    # 检查宽高比例
                    ratio = width / height
                    if ratio > 5 or ratio < 0.2:
                        logger.info(f"Skipping abnormal aspect ratio: {img_src} (ratio: {ratio:.2f})")
                        return True
                        
                    # 图片通过所有检查
                    return False
                    
                except Exception as e:
                    # logger.warning(f"Failed to check image dimensions for {img_src}: {str(e)}")
                    return True  # 出错时跳过图片
            
            # 如果应该跳过该图片
            if should_skip_image():
                stats['skipped'] += 1
                image_hash_cache[img_src] = '' if not is_multimodal else None
                return '' if not is_multimodal else None
            
            # 如果是多模态处理模式，在通过大小和尺寸检查后再进行多模态处理
            if is_multimodal:
                logger.info(f"Processing image with multimodal model: {img_src}")
                # 构建提示词，替换主题
                prompt = sample_prompt.replace("{theme}", theme) if theme else sample_prompt
                
                # 调用gemma3 API进行图片识别
                try:
                    result = call_gemma3_api(prompt=prompt, image_url=img_src)
                    
                    if result and isinstance(result, dict) and "describe" in result:
                        # 将图片描述添加到FAISS索引
                        description = result.get("describe", "")
                        if description and len(description) > 10:  # 确保描述有足够的内容
                            # 准备要存储的数据
                            data = {
                                "image_url": img_src,
                                "task_id": task_id,
                                "description": description,
                                "is_related": result.get("is_related", False),
                                "is_deleted": result.get("is_deleted", False)
                            }
                            
                            # 添加到FAISS索引
                            try:
                                # 获取FAISS索引实例
                                current_faiss_index = get_streamlit_faiss_index()
                                add_to_faiss_index(description, data, current_faiss_index)
                                logger.info(f"Added image description to FAISS index: {img_src}")
                                
                                # 保存更新后的索引到磁盘
                                from utils.embedding_utils import save_faiss_index
                                save_faiss_index(current_faiss_index, INDEX_DIR)
                                logger.info(f"Saved updated FAISS index to disk with {current_faiss_index.get_size()} items")
                            except Exception as e:
                                # logger.error(f"Failed to add to FAISS index: {str(e)}")
                                pass
                        
                        # 缓存结果
                        image_hash_cache[img_src] = result
                        return result
                    else:
                        logger.warning(f"Invalid or empty result from gemma3 API for {img_src}")
                        image_hash_cache[img_src] = None
                        return None
                except Exception as e:
                    logger.error(f"Error calling gemma3 API: {str(e)}")
                    image_hash_cache[img_src] = None
                    return None
            
            # 计算图片内容的MD5哈希值
            content_hash = hashlib.md5(content).hexdigest()
            
            # 检查是否已经下载过相同内容的图片
            for cached_url, cached_path in image_hash_cache.items():
                if isinstance(cached_path, str) and cached_url != img_src and cached_path.startswith(str(IMAGES_DIR / task_id)) and Path(cached_path).exists():
                    try:
                        with open(cached_path, 'rb') as f:
                            cached_content = f.read()
                            cached_hash = hashlib.md5(cached_content).hexdigest()
                            if cached_hash == content_hash:
                                logger.info(f"Duplicate image content detected. Using existing file: {cached_path}")
                                image_hash_cache[img_src] = cached_path
                                stats['cached'] += 1
                                return cached_path
                    except Exception as e:
                        logger.warning(f"Error checking cached file {cached_path}: {str(e)}")
            
            # 注意：图片尺寸检查已经在前面完成，这里不需要重复检查
                
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
                stats['cached'] += 1
                return str(file_path)
            
            # 保存图片 - 使用同步文件操作
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # 保存图片URL映射
            try:
                url_mapper = ImageUrlMapper(IMAGES_DIR)
                url_mapper.save_url_mapping(task_id, file_name, img_src)
                logger.info(f"Saved URL mapping: {file_name} -> {img_src}")
            except Exception as e:
                logger.error(f"Failed to save URL mapping: {str(e)}")
                
            image_hash_cache[img_src] = str(file_path)
            stats['success'] += 1
            return str(file_path)
            
    except Exception as e:
        stats['failed'] += 1
        image_hash_cache[img_src] = ''
        return ''

async def text_from_html(body: str, session: aiohttp.ClientSession, task_id: str, is_multimodal: bool = False, theme: str = "") -> Dict[str, any]:
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
            base_url = None
            
            # 尝试提取基础URL，用于解析相对路径
            try:
                # 从页面中提取基础URL
                base_tag = soup.find('base', href=True)
                if base_tag and base_tag.get('href'):
                    base_url = base_tag['href']
                    logger.info(f"Found base URL tag: {base_url}")
                else:
                    # 尝试从meta标签中提取URL
                    meta_url = None
                    for meta in soup.find_all('meta', property=['og:url', 'twitter:url']):
                        meta_url = meta.get('content')
                        if meta_url:
                            base_url = meta_url
                            logger.info(f"Found base URL from meta tag: {base_url}")
                            break
                    
                    # 如果还是没有找到，尝试从canonical链接中提取
                    if not base_url:
                        canonical = soup.find('link', rel='canonical')
                        if canonical and canonical.get('href'):
                            base_url = canonical.get('href')
                            logger.info(f"Found base URL from canonical link: {base_url}")
            except Exception as e:
                logger.warning(f"Error extracting base URL: {str(e)}")
                
            # 初始化统计字典
            stats = {
                'total': len(img_tags),
                'success': 0,
                'failed': 0,
                'cached': 0,
                'skipped': 0
            }
            
            # 处理所有图片标签
            for img in img_tags:
                img_src = img.get('src', '')
                
                # 跳过数据图片和空路径
                if not img_src or img_src.startswith('data:'):
                    stats['skipped'] += 1
                    continue
                    
                # 处理相对路径
                if img_src.startswith('//'):
                    # 协议相对路径
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    # 绝对路径，需要基础URL
                    if base_url:
                        # 使用基础URL解析
                        img_src = urllib.parse.urljoin(base_url, img_src)
                    else:
                        # 尝试从页面URL提取域名
                        try:
                            domain = urllib.parse.urlparse(soup.get('url', '')).netloc
                            if domain:
                                img_src = f"https://{domain}{img_src}"
                        except:
                            # 如果无法解析，跳过该图片
                            logger.warning(f"Cannot resolve relative path: {img_src}")
                            continue
                elif not img_src.startswith(('http://', 'https://')):
                    # 其他相对路径
                    if base_url:
                        img_src = urllib.parse.urljoin(base_url, img_src)
                    else:
                        # 尝试从页面的URL属性或其他属性中提取域名
                        try:
                            # 尝试从页面属性中获取URL
                            page_url = None
                            if hasattr(soup, 'url'):
                                page_url = soup.url
                            elif hasattr(soup, 'original_url'):
                                page_url = soup.original_url
                            
                            # 检查搜狗特定域名
                            if 'sogou' in img_src or 'soso' in img_src:
                                if img_src.startswith('./'):
                                    img_src = 'https://www.sogou.com/' + img_src[2:]
                                else:
                                    img_src = 'https://www.sogou.com/' + img_src
                                logger.info(f"Fixed Sogou relative path: {img_src}")
                            elif page_url:
                                # 从页面URL提取域名
                                parsed_url = urllib.parse.urlparse(page_url)
                                domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                img_src = urllib.parse.urljoin(domain, img_src)
                                logger.info(f"Resolved relative path using page URL: {img_src}")
                            else:
                                logger.warning(f"Cannot resolve relative path without base URL: {img_src}")
                                continue
                        except Exception as e:
                            logger.warning(f"Error resolving relative path: {str(e)}, path: {img_src}")
                            continue
                
                # 添加下载图片的异步任务
                img_tasks.append(download_image(session, img_src, image_hash_cache, task_id, is_multimodal=is_multimodal, theme=theme, stats=stats))
            
            # 等待所有图片下载完成
            img_paths = await asyncio.gather(*img_tasks)
            img_paths = [path for path in img_paths if path]  # 过滤空路径
            
            # 输出图片下载统计信息
            logger.info(f"图片下载统计: 总计 {stats['total']} 张, 成功 {stats['success']} 张, 失败 {stats['failed']} 张, 使用缓存 {stats['cached']} 张, 跳过 {stats['skipped']} 张")
        
        return {
            'text': text_content,
            'images': img_paths
        }
        
    except Exception as e:
        logger.error(f"Error processing HTML content: {str(e)}")
        return {'text': '', 'images': []}

async def fetch(browser, url: str, task_id: str, is_multimodal: bool = False, theme: str = "") -> Dict[str, any]:
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
            # 设置请求拦截器来记录重定向
            await page.route("**/*", lambda route: route.continue_())
            
            # 访问 URL，并等待完成所有重定向
            response = await page.goto(url, timeout=60000, wait_until="networkidle")
            
            # 获取最终 URL（重定向后）
            final_url = page.url
            
            # 如果 URL 发生了变化，记录下来
            if final_url != url:
                logger.info(f"URL redirected: {url} -> {final_url}")
                
            content = await page.content()
            result = await text_from_html(content, session, task_id, is_multimodal=is_multimodal, theme=theme)
            return {
                'url': final_url,  # 返回最终 URL，而不是原始 URL
                'original_url': url,  # 保存原始 URL 以便跟踪
                'content': result['text'],
                'images': result['images']
            }
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return {'url': url, 'content': '', 'images': []}
        finally:
            await page.close()
            await context.close()

async def get_main_content(url_list: List[str], task_id: str = None, is_multimodal: bool = False, theme: str = "") -> List[Dict[str, any]]:
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
            
            tasks = [fetch(browser, url, task_id, is_multimodal=is_multimodal, theme=theme) for url in url_list]
            results = await asyncio.gather(*tasks)
            return results, task_id
        finally:
            await browser.close()

if __name__ == '__main__':
    url_list = ['http://news.china.com.cn/2024-11/18/content_117554263.shtml']
    main_content = asyncio.run(get_main_content(url_list, task_id="test_task"))
    if main_content:
        print(main_content)
    else:
        print("Failed to retrieve the main content.")