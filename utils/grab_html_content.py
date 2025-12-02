import os
import sys
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
from utils.openai_vl_process import process_image, process_image_async
from utils.embedding_utils import add_to_faiss_index, create_faiss_index
from utils.image_filter import (
    should_skip_image_url,
    is_likely_icon_by_dimensions,
    is_low_quality_image,
    MIN_WIDTH, MIN_HEIGHT, MIN_AREA,
    MIN_FILE_SIZE as FILTER_MIN_FILE_SIZE,
)
import concurrent.futures
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
logger = logging.getLogger(__name__)

# 定义FAISS索引目录，但不在模块级别初始化索引
# 根据用户和文章ID动态创建索引
INDEX_DIR = 'data/faiss'
# 全局索引变量，但不在模块级别初始化
faiss_index = None

# 导入embedding_utils中的全局缓存，避免循环导入
try:
    from utils.embedding_utils import global_faiss_index_cache as faiss_index_cache
except ImportError:
    # 如果无法导入，创建本地缓存
    faiss_index_cache = {}

def get_streamlit_faiss_index(username: str = None, article_id: str = None):
    """获取FAISS索引实例，优先从缓存获取，然后从磁盘加载用户和文章特定的索引"""
    global faiss_index, INDEX_DIR, faiss_index_cache
    
    # 构建索引缓存键
    cache_key = f"{username or 'global'}/{article_id or 'default'}"
    
    # 记录请求的索引路径，用于调试
    expected_path = ""
    if username and article_id:
        expected_path = f"{INDEX_DIR}/{username}/{article_id}"
    elif username:
        expected_path = f"{INDEX_DIR}/{username}"
    else:
        expected_path = INDEX_DIR
    
    logger.debug(f"Requesting FAISS index for path: {expected_path}")
    
    # 首先检查缓存中是否已有该索引
    if cache_key in faiss_index_cache:
        logger.debug(f"Using cached FAISS index for {cache_key}")
        cached_index = faiss_index_cache[cache_key]
        # 验证索引是否有效
        try:
            index_size = cached_index.get_size()
            logger.info(f"Using cached FAISS index for {cache_key} with {index_size} items")
            return cached_index
        except Exception as e:
            logger.warning(f"Cached index for {cache_key} is invalid: {e}, will reload")
            # 如果缓存的索引无效，从缓存中删除
            del faiss_index_cache[cache_key]
    
    # 如果指定了用户名和文章ID，尝试加载文章特定的索引
    if username and article_id:
        try:
            article_faiss_index = create_faiss_index(load_from_disk=True, index_dir=INDEX_DIR, username=username, article_id=article_id)
            index_size = article_faiss_index.get_size()
            logger.debug(f"Loaded article-specific FAISS index for {username}/{article_id} with {index_size} items")
            if index_size == 0:
                logger.debug(f"Article-specific index for {username}/{article_id} is empty")
            # 将加载的索引添加到缓存
            faiss_index_cache[cache_key] = article_faiss_index
            return article_faiss_index
        except Exception as e:
            logger.warning(f"Failed to load article-specific index for {username}/{article_id}: {e}")
    
    # 如果指定了用户名，尝试加载用户特定的索引
    if username:
        try:
            user_cache_key = f"{username}/default"
            user_faiss_index = create_faiss_index(load_from_disk=True, index_dir=INDEX_DIR, username=username)
            index_size = user_faiss_index.get_size()
            logger.debug(f"Loaded user-specific FAISS index for {username} with {index_size} items")
            if index_size == 0:
                logger.debug(f"User-specific index for {username} is empty")
            # 将加载的索引添加到缓存
            faiss_index_cache[user_cache_key] = user_faiss_index
            return user_faiss_index
        except Exception as e:
            logger.warning(f"Failed to load user-specific index for {username}: {e}")
    
    # 如果全局索引为None，初始化它
    if faiss_index is None:
        logger.debug("Initializing global FAISS index for the first time")
        faiss_index = create_faiss_index(load_from_disk=True, index_dir=INDEX_DIR)
        index_size = faiss_index.get_size()
        logger.debug(f"Global FAISS index initialized with {index_size} items")
        if index_size == 0:
            logger.warning("Global FAISS index is empty")
        # 将全局索引添加到缓存
        faiss_index_cache['global/default'] = faiss_index
    
    return faiss_index

# 常量配置
MIN_IMAGE_SIZE = 8 * 1024  # 降低到8KB，支持webp等高度优化的格式
VALID_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'}  # 增加更多图片格式
IMAGES_DIR = Path('images')
IMAGES_DIR.mkdir(exist_ok=True)

# 重试配置
MAX_RETRIES = 1  # 增加最大重试次数
RETRY_DELAY = 2  # 增加重试延迟（秒）

# 不进行重试的HTTP状态码
NON_RETRYABLE_STATUS_CODES = {403, 404, 410, 451}  # 禁止访问、不存在、已删除、法律原因

# 不进行重试的错误模式
NON_RETRYABLE_ERROR_PATTERNS = [
    "certificate",  # 证书错误
    "ssl",          # SSL错误
    "ConnectError", # 连接错误
    "ConnectionRefused", # 连接被拒绝
    "No route to host", # 无法路由到主机
    "Name or service not known" # DNS解析失败
]

# 可重试的错误模式 - 这些错误通常是临时的，可以重试
RETRYABLE_ERROR_PATTERNS = [
    "timed out",    # 超时错误 - 可能是临时网络问题
    "timeout",      # 另一种超时表述
    "reset by peer", # 连接被对方重置
    "TooManyRedirects", # 重定向过多
    "ChunkedEncodingError", # 分块编码错误
    "IncompleteRead"  # 不完整读取
]

# 全局URL映射缓存 - 用于跨会话去重
# 格式: {normalized_url: {content_hash: hash, path: file_path}}
GLOBAL_URL_MAPPING = {}

# 全局内容哈希映射 - 用于快速查找相同内容的图片
# 格式: {content_hash: {path: file_path, urls: [url1, url2, ...]}}
GLOBAL_CONTENT_HASH_MAPPING = {}

# 使用于模型校验的最小尺寸（HEAD Content-Length）- 提高阈值
MIN_MODEL_IMAGE_SIZE = 15 * 1024  # 15KB - 更严格的阈值

async def is_valid_image_url_for_model(session: aiohttp.ClientSession, url: str) -> bool:
    """通过轻量校验避免将无效/不支持的图片URL传给多模态/嵌入模型。
    规则：
    - 必须是http/https
    - 过滤data:、空URL
    - 过滤广告跟踪域名和URL模式
    - 后缀或Content-Type不得为svg
    - 通过HEAD获取Content-Type应为image/*；若有Content-Length则不小于MIN_MODEL_IMAGE_SIZE
    """
    if not url:
        return False
    u = url.strip()
    if u.startswith('data:'):
        return False
    if not (u.startswith('http://') or u.startswith('https://')):
        return False
    lower = u.lower()
    
    # 过滤广告跟踪域名
    ad_domains = [
        'kunyu.csdn.net',      # CSDN广告网络
        'ad.csdn.net',         # CSDN广告
        'ads.csdn.net',        # CSDN广告
        'googleads.g.doubleclick.net',  # Google广告
        'pagead2.googlesyndication.com', # Google广告
        'doubleclick.net',     # 广告网络
        'googlesyndication.com', # Google广告联盟
        'adservice.google.com', # Google广告服务
        'amazon-adsystem.com',  # 亚马逊广告
        'scorecardresearch.com', # 广告跟踪
        'advertising.com',     # 广告
        'adnxs.com',          # AppNexus广告
        'adsrvr.org',         # Trade Desk广告
    ]
    
    # 检查是否为广告域名
    from urllib.parse import urlparse
    try:
        parsed = urlparse(u)
        domain = parsed.netloc.lower()
        for ad_domain in ad_domains:
            if ad_domain in domain:
                logger.debug(f"Filtered ad domain: {url}")
                return False
    except Exception:
        pass
    
    # 过滤包含广告标识的URL
    ad_indicators = [
        'adid=', 'ad_id=', 'adblockflag=', 'ad_block',
        'advertisement', 'ad_banner', 'ad_image',
        'tracking_pixel', 'track_pixel', 'beacon',
        'ad.png', 'ad.jpg', 'ad.gif', 'ad.webp',
        'banner.png', 'banner.jpg', 'banner.gif',
        '/ads/', '/ad/', '/advertisement/',
    ]
    
    for indicator in ad_indicators:
        if indicator in lower:
            logger.debug(f"Filtered ad indicator URL: {url}")
            return False
    
    # 先用后缀粗过滤svg
    if lower.endswith('.svg') or 'format=svg' in lower:
        return False
    # 用HEAD验证资源可达和类型
    try:
        timeout = aiohttp.ClientTimeout(total=8, connect=5)
        async with session.head(u, ssl=False, allow_redirects=True, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            ctype = resp.headers.get('Content-Type', '').lower()
            # 过滤svg
            if 'image/svg' in ctype:
                return False
            if not ctype.startswith('image/'):
                return False
            cl = resp.headers.get('Content-Length')
            if cl is not None:
                try:
                    if int(cl) < MIN_MODEL_IMAGE_SIZE:
                        return False
                except Exception:
                    pass
            return True
    except Exception:
        # 有些服务器不支持HEAD，尝试GET前几个字节
        try:
            timeout = aiohttp.ClientTimeout(total=8, connect=5)
            async with session.get(u, ssl=False, allow_redirects=True, timeout=timeout) as resp:
                if resp.status != 200:
                    return False
                ctype = resp.headers.get('Content-Type', '').lower()
                if 'image/svg' in ctype:
                    return False
                if not ctype.startswith('image/'):
                    return False
                return True
        except Exception:
            return False

# 创建一个全局的ThreadPoolExecutor，使用线程锁保护其访问
_EXECUTOR_LOCK = threading.Lock()
_EXECUTOR = None

def get_executor():
    """获取全局ThreadPoolExecutor实例，如果不存在则创建"""
    global _EXECUTOR
    with _EXECUTOR_LOCK:
        if _EXECUTOR is None:
            _EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        return _EXECUTOR

def shutdown_executor():
    """安全关闭全局ThreadPoolExecutor"""
    global _EXECUTOR
    with _EXECUTOR_LOCK:
        if _EXECUTOR is not None:
            _EXECUTOR.shutdown(wait=True)
            _EXECUTOR = None

def tag_visible(element) -> bool:
    """
    判断HTML元素是否应该可见
    """
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]', 'button', 'a']:
        return False
    if isinstance(element, Comment):
        return False
    return True

async def download_image(session: aiohttp.ClientSession, img_src: str, image_hash_cache: dict, task_id: str, is_multimodal: bool = False, use_direct_image_embedding: bool = False, theme: str = "", stats: dict = None, base_url: str = None, username: str = None, article_id: str = None) -> Union[str, dict]:
    """
    异步下载图片，使用MD5哈希确保每张图片只下载一次
    
    Args:
        session: aiohttp客户端会话
        img_src: 图片URL
        image_hash_cache: 图片哈希缓存字典，格式为 {url: path_or_result} 或 {content_hash: {path: path, urls: [url1, url2, ...]}}
        task_id: 任务ID
        is_multimodal: 是否使用多模态模型处理图片，默认为False
        theme: 主题，用于多模态模型判断图片相关性
        stats: 统计字典，用于记录成功和失败的下载数量
        base_url: 页面基础URL，用于设置Referer
        
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
            'skipped': 0,
            'duplicate': 0
        }
    
    # 处理并规范化图片URL
    normalized_img_src = normalize_image_url(img_src, base_url)
    if not normalized_img_src:
        stats['skipped'] += 1 if stats else 0
        return '' if not is_multimodal else None
        
    # === 新增：URL预筛选 - 在下载前过滤明显的非内容图片 ===
    if should_skip_image_url(normalized_img_src):
        stats['skipped'] = stats.get('skipped', 0) + 1
        logger.debug(f"URL pre-filter skipped: {normalized_img_src[:80]}...")
        image_hash_cache[normalized_img_src] = '' if not is_multimodal else None
        return '' if not is_multimodal else None
    
    # 检查URL是否已经在当前会话缓存中
    if normalized_img_src in image_hash_cache:
        stats['cached'] += 1
        logger.debug(f"Using cached image URL: {normalized_img_src}")
        return image_hash_cache[normalized_img_src]
        
    # 检查URL是否在全局缓存中
    global GLOBAL_URL_MAPPING
    if normalized_img_src in GLOBAL_URL_MAPPING:
        cached_info = GLOBAL_URL_MAPPING[normalized_img_src]
        file_path = cached_info['path']
        
        if Path(file_path).exists():
            # 将缓存信息添加到当前会话缓存
            image_hash_cache[normalized_img_src] = file_path
            stats['cached'] += 1
            logger.debug(f"Using globally cached image URL: {normalized_img_src}")
            return file_path
    
    # 提取域名用于特殊处理
    parsed_url = urllib.parse.urlparse(normalized_img_src)
    domain = parsed_url.netloc
    
    # 检查是否有相同URL模式的图片已经下载过
    # 例如：去除查询参数后的URL相同
    base_img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    for cached_url in image_hash_cache:
        if isinstance(cached_url, str) and cached_url.startswith('http'):
            parsed_cached = urllib.parse.urlparse(cached_url)
            base_cached_url = f"{parsed_cached.scheme}://{parsed_cached.netloc}{parsed_cached.path}"
            
            # 如果基础URL相同（忽略查询参数），使用已缓存的图片
            if base_img_url == base_cached_url and image_hash_cache[cached_url]:
                stats['duplicate'] = stats.get('duplicate', 0) + 1
                logger.debug(f"Found similar URL pattern, using cached: {cached_url}")
                image_hash_cache[normalized_img_src] = image_hash_cache[cached_url]
                return image_hash_cache[cached_url]
        
    # 直接URL嵌入模式：下载图片内容进行尺寸筛选，合格则收集URL
    # 注意：这里不再逐张做 embedding，避免与 searxng_utils.py 的批量处理重复
    if use_direct_image_embedding:
        try:
            # 先做基本的URL校验
            valid = await is_valid_image_url_for_model(session, normalized_img_src)
        except Exception:
            valid = False
        if not valid:
            logger.debug(f"Skip direct embedding due to validation failure: {normalized_img_src}")
            if stats is not None:
                stats['skipped'] = stats.get('skipped', 0) + 1
            image_hash_cache[normalized_img_src] = None
            return None
        
        # 下载图片内容进行尺寸筛选
        try:
            timeout = aiohttp.ClientTimeout(total=15, connect=10)
            async with session.get(normalized_img_src, ssl=False, timeout=timeout, allow_redirects=True) as resp:
                if resp.status != 200:
                    stats['failed'] = stats.get('failed', 0) + 1
                    image_hash_cache[normalized_img_src] = None
                    return None
                content = await resp.read()
                
                # 使用增强的图片筛选逻辑
                is_filtered, filter_reason, image_info = is_low_quality_image(
                    content=content,
                    url=normalized_img_src,
                    check_url=False,  # URL已在前面检查过
                    check_dimensions=True,
                    check_file_size=True,
                    check_content=True,
                )
                
                if is_filtered:
                    stats['skipped'] = stats.get('skipped', 0) + 1
                    logger.debug(f"Direct embedding filtered: {filter_reason} - {normalized_img_src[:60]}...")
                    image_hash_cache[normalized_img_src] = None
                    return None
        except Exception as e:
            logger.debug(f"Error downloading image for filtering: {e}")
            stats['failed'] = stats.get('failed', 0) + 1
            image_hash_cache[normalized_img_src] = None
            return None
        
        # 通过筛选，收集URL用于后续批量嵌入
        logger.debug(f"收集图片URL用于后续批量嵌入: {normalized_img_src[:50]}...")
        result = {"image_url": normalized_img_src, "embedding_method": "deferred_batch"}
        image_hash_cache[normalized_img_src] = result
        stats['success'] = stats.get('success', 0) + 1
        return result

    # 多模态模式：先校验，合格则无需下载图片内容，直接调用识别并入库
    if is_multimodal:
        # 对 CSDN 图片采用本地下载再以base64传给多模态，避免直链受限
        if ('csdnimg.cn' in domain) or ('csdn.net' in domain and 'csdnimg' in domain):
            try:
                logger.debug(f"CSDN image detected, using local download + base64 for multimodal: {normalized_img_src}")
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                ]
                headers = {
                    'User-Agent': random.choice(user_agents),
                    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Referer': 'https://blog.csdn.net/',
                    'Origin': 'https://blog.csdn.net',
                    'Host': domain
                }
                timeout = aiohttp.ClientTimeout(total=15, connect=10)
                async with session.get(normalized_img_src, ssl=False, headers=headers, timeout=timeout, allow_redirects=True) as resp:
                    if resp.status != 200:
                        logger.debug(f"CSDN image download failed status={resp.status}: {normalized_img_src}")
                        image_hash_cache[normalized_img_src] = None
                        stats['failed'] += 1 if stats else 0
                        return None
                    content = await resp.read()
                if not content or len(content) < MIN_MODEL_IMAGE_SIZE:
                    logger.debug(f"CSDN image too small or empty: {normalized_img_src} size={len(content) if content else 0}")
                    image_hash_cache[normalized_img_src] = None
                    stats['skipped'] += 1 if stats else 0
                    return None
                # 发送为base64
                try:
                    logger.debug(
                        "Multimodal sending (CSDN base64) image_url=%s bytes=%d task_id=%s",
                        normalized_img_src, len(content), task_id,
                    )
                    # 使用异步版本，避免阻塞事件循环
                    result = await process_image_async(image_content=content)
                except asyncio.CancelledError:
                    logger.debug(f"CSDN multimodal skipped (cancelled): {normalized_img_src}")
                    image_hash_cache[normalized_img_src] = None
                    stats['skipped'] += 1 if stats else 0
                    return None
                except Exception as e:
                    logger.debug(
                        "CSDN multimodal via base64 failed: %s (%s) | url=%s",
                        str(e) or "Unknown error", type(e).__name__, normalized_img_src
                    )
                    image_hash_cache[normalized_img_src] = None
                    stats['failed'] += 1 if stats else 0
                    return None

                if result and isinstance(result, dict) and "describe" in result:
                    description = result.get("describe", "")
                    if description and len(description) > 10:
                        data = {"image_url": normalized_img_src, "task_id": task_id, "description": description}
                        try:
                            current_faiss_index = get_streamlit_faiss_index(username=username, article_id=article_id)
                            before_size = current_faiss_index.get_size()
                            add_to_faiss_index(description, data, current_faiss_index, username=username, article_id=article_id, auto_save=True)
                            after_size = current_faiss_index.get_size()
                            if after_size > before_size:
                                logger.debug(f"已添加图片描述到FAISS索引: {normalized_img_src}")
                        except Exception as e:
                            logger.error(f"记录图片描述到FAISS索引失败: {str(e)}")
                    image_hash_cache[normalized_img_src] = result
                    stats['success'] += 1 if stats else 0
                    return result
                else:
                    logger.debug(f"Multimodal returned empty/invalid for CSDN {normalized_img_src}")
                    image_hash_cache[normalized_img_src] = None
                    stats['failed'] += 1 if stats else 0
                    return None
            except Exception as e:
                # 这里捕获的是下载阶段的错误（非多模态处理错误）
                logger.debug(f"CSDN image download/processing error: {str(e) or 'Unknown'} | url={normalized_img_src}")
                image_hash_cache[normalized_img_src] = None
                stats['failed'] += 1 if stats else 0
                return None
        else:
            try:
                valid = await is_valid_image_url_for_model(session, normalized_img_src)
            except Exception:
                valid = False
            if not valid:
                logger.debug(f"Skip multimodal due to validation failure: {normalized_img_src}")
                if stats is not None:
                    stats['skipped'] = stats.get('skipped', 0) + 1
                image_hash_cache[normalized_img_src] = None
                return None
            logger.debug(f"Fast-path multimodal processing for image URL: {normalized_img_src}")
            try:
                # 重要：在调用多模态前打印即将发送的图片和上下文，便于定位400错误
                logger.info(
                    "Multimodal sending image_url=%s task_id=%s user=%s article_id=%s",
                    normalized_img_src, task_id, username, article_id,
                )
                # 使用异步版本，避免阻塞事件循环，实现真正的并发处理
                result = await process_image_async(image_url=normalized_img_src)
                if result and isinstance(result, dict) and "describe" in result:
                    description = result.get("describe", "")
                    if description and len(description) > 10:
                        data = {"image_url": normalized_img_src, "task_id": task_id, "description": description}
                        try:
                            current_faiss_index = get_streamlit_faiss_index(username=username, article_id=article_id)
                            before_size = current_faiss_index.get_size()
                            add_to_faiss_index(description, data, current_faiss_index, username=username, article_id=article_id, auto_save=True)
                            after_size = current_faiss_index.get_size()
                            if after_size > before_size:
                                logger.debug(f"已添加图片描述到FAISS索引: {normalized_img_src}")
                        except Exception as e:
                            logger.error(f"记录图片描述到FAISS索引失败: {str(e)}")
                    image_hash_cache[normalized_img_src] = result
                    stats['success'] += 1 if stats else 0
                    return result
                else:
                    logger.debug(f"Multimodal returned empty/invalid for {normalized_img_src}")
                    image_hash_cache[normalized_img_src] = None
                    stats['failed'] += 1 if stats else 0
                    return None
            except Exception as e:
                # 重要：错误时也打印发送的图片URL和上下文
                logger.error(
                    "Multimodal fast-path error: %s | image_url=%s task_id=%s user=%s article_id=%s",
                    str(e), normalized_img_src, task_id, username, article_id,
                )
                image_hash_cache[normalized_img_src] = None
                stats['failed'] += 1 if stats else 0
                return None

    try:
        # 设置基础请求头，模拟浏览器行为
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        ]
        
        # 默认请求头
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site'
        }
        
        # 设置合适的Referer
        if base_url:
            headers['Referer'] = base_url
        else:
            # 使用图片所在域名作为Referer
            headers['Referer'] = f"{parsed_url.scheme}://{domain}/"
        
        # 针对特定网站的特殊处理
        if 'csdnimg.cn' in domain:
            # CSDN图片特殊处理
            headers.update({
                'Referer': 'https://blog.csdn.net/',
                'Origin': 'https://blog.csdn.net',
                'Host': domain
            })
        elif 'zhihu.com' in domain or 'zhimg.com' in domain:
            # 知乎图片特殊处理
            headers.update({
                'Referer': 'https://www.zhihu.com/',
                'Origin': 'https://www.zhihu.com'
            })
        elif 'jianshu' in domain:
            # 简书图片特殊处理
            headers.update({
                'Referer': 'https://www.jianshu.com/',
                'Origin': 'https://www.jianshu.com'
            })
        elif '126.net' in domain:
            # 网易图片特殊处理
            logger.debug(f"处理网易图片URL: {img_src}")
            # 如果是网易的URL，尝试提取实际图片URL
            if 'url=' in img_src:
                try:
                    # 提取实际的图片URL
                    query_params = parse_qs(parsed_url.query)
                    if 'url' in query_params:
                        actual_img_url = query_params['url'][0]
                        img_src = actual_img_url
                        # 更新解析后的URL
                        parsed_url = urllib.parse.urlparse(img_src)
                        domain = parsed_url.netloc
                except Exception as e:
                    pass
            headers.update({
                'Referer': 'https://www.163.com/',
                'Origin': 'https://www.163.com'
            })
        
        # 实现智能重试机制
        retry_count = 0
        max_retries = MAX_RETRIES  # 使用配置的重试次数
        success = False
        last_error = None
        content = None
        
        # 检查域名是否在已知的高失败率域名列表中
        high_failure_domains = ['toutiaoimg.com', 'toutiao.com', 'weibo.cn', 'sinaimg.cn', 'byteimg.com', 'gov.cn', 'chinadaily.com.cn']
        medium_failure_domains = ['jschina.com.cn']
        
        if any(fail_domain in domain for fail_domain in high_failure_domains):
            # 对于已知的高失败率域名，减少重试次数但不完全放弃
            max_retries = 1
            logger.debug(f"Reducing retries for high-failure domain {domain}: {img_src}")
        elif any(fail_domain in domain for fail_domain in medium_failure_domains):
            # 对于中等失败率的域名，保持适中的重试次数
            max_retries = 2
            logger.debug(f"Using medium retry count for domain {domain}: {img_src}")
        
        while retry_count <= max_retries and not success:
            try:
                # 每次重试使用不同的User-Agent
                headers['User-Agent'] = random.choice(user_agents)
                
                # 设置超时，随重试次数增加
                timeout = aiohttp.ClientTimeout(total=10 + retry_count * 5)
                
                # 尝试使用不同的请求方式
                if retry_count > 0:
                    # 尝试不同的Referer策略
                    if retry_count % 3 == 1:
                        # 使用Google作为Referer
                        headers['Referer'] = 'https://www.google.com/'
                    elif retry_count % 3 == 2:
                        # 使用图片直接URL作为Referer
                        headers['Referer'] = img_src
                    
                    # 针对CSDN的特殊处理
                    if 'csdnimg.cn' in domain and retry_count > 1:
                        # 尝试不同的CSDN Referer格式
                        csdn_referers = [
                            'https://blog.csdn.net/article/details',
                            'https://blog.csdn.net/weixin_44621343/article/details',
                            'https://download.csdn.net/download'
                        ]
                        headers['Referer'] = csdn_referers[retry_count % len(csdn_referers)]
                
                # 尝试下载图片
                try:
                    # 使用适当的超时时间，防止卡死
                    # 每次重试增加超时时间，但不超过30秒
                    timeout = aiohttp.ClientTimeout(total=min(30, 10 + retry_count * 5), connect=10)
                    
                    # 对于某些特定域名，尝试使用不同的协议
                    if retry_count > 0 and 'gov.cn' in domain:
                        # 尝试将https切换为http，或反之
                        if img_src.startswith('https://'):
                            alt_img_src = img_src.replace('https://', 'http://')
                        elif img_src.startswith('http://'):
                            alt_img_src = img_src.replace('http://', 'https://')
                        else:
                            alt_img_src = img_src
                            
                        logger.debug(f"Trying alternative protocol for gov.cn domain: {alt_img_src}")
                        img_src = alt_img_src
                    
                    # 使用超时保护进行请求
                    try:
                        async with session.get(img_src, ssl=False, headers=headers, timeout=timeout, allow_redirects=True) as response:
                            if response.status == 200:
                                content = await response.read()
                                success = True
                                break
                            else:
                                status_code = response.status
                                logger.debug(f"Failed to download image {img_src}, status: {status_code}, retry: {retry_count+1}/{max_retries+1}")
                                last_error = f"HTTP status {status_code}"
                                
                                # 对于特定状态码，不再重试
                                if status_code in NON_RETRYABLE_STATUS_CODES:
                                    logger.debug(f"Skipping retries for non-retryable status code {status_code}: {img_src}")
                                    break
                                
                                # 对于重定向状态码，尝试获取重定向URL
                                if status_code in (301, 302, 303, 307, 308) and 'Location' in response.headers:
                                    redirect_url = response.headers['Location']
                                    logger.debug(f"Following redirect from {img_src} to {redirect_url}")
                                    img_src = redirect_url
                    except aiohttp.ClientError as e:
                        logger.debug(f"Client error for {img_src}: {str(e)}, retry: {retry_count+1}/{max_retries+1}")
                        last_error = str(e)
                except aiohttp.ClientConnectorError as e:
                    # 特殊处理连接错误
                    error_msg = str(e)
                    logger.debug(f"Connection error for {img_src}: {error_msg}, retry: {retry_count+1}/{max_retries+1}")
                    last_error = error_msg
                        
            except Exception as e:
                error_msg = str(e)
                logger.debug(f"Error downloading image {img_src}: {error_msg}, retry: {retry_count+1}/{max_retries+1}")
                last_error = error_msg
                
                # 检查是否是不应该重试的错误类型
                should_skip_retry = any(pattern in error_msg.lower() for pattern in NON_RETRYABLE_ERROR_PATTERNS)
                if should_skip_retry:
                    logger.debug(f"Skipping retries for non-retryable error pattern: {error_msg}")
                    break
                    
                # 检查是否是应该重试的错误类型
                should_retry = any(pattern in error_msg.lower() for pattern in RETRYABLE_ERROR_PATTERNS)
                if should_retry:
                    logger.debug(f"Will retry for retryable error pattern: {error_msg}")
                    # 对于超时错误，增加额外的等待时间
                    if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                        await asyncio.sleep(retry_count + 2)  # 额外等待时间
            
            # 如果失败，等待后重试
            retry_count += 1
            if retry_count <= max_retries:
                # 使用指数退避策略，但添加随机抖动以避免同时重试
                jitter = random.uniform(0.5, 1.5)  # 随机抖动因子
                delay = RETRY_DELAY * (2 ** (retry_count - 1)) * jitter  # 指数退避 + 随机抖动
                logger.debug(f"Waiting {delay:.2f}s before retry {retry_count} for {img_src}")
                await asyncio.sleep(delay)
        
        if not success:
            # 使用warning级别记录，以便更容易在日志中发现
            logger.debug(f"Failed to download image after {retry_count} attempts: {img_src}, last error: {last_error}")
            stats['failed'] += 1 if stats else 0
            
            # 检查是否是特定域名的错误，可能需要特殊处理
            if any(special_domain in domain for special_domain in ['gov.cn', 'chinadaily.com.cn', 'jschina.com.cn']):
                # 对于这些特定域名，我们不将其标记为永久失败，以便将来可能重试
                logger.debug(f"Not caching failure for special domain {domain}: {img_src}")
                return '' if not is_multimodal else None
            else:
                # 将URL添加到图片哈希缓存中，标记为失败，避免将来重试
                image_hash_cache[normalized_img_src] = '' if not is_multimodal else None
                return '' if not is_multimodal else None
            
        # 成功获取响应
        if not content:  # 如果内容还没有读取，则读取
            content = await response.read()
        content_size = len(content)
        
        # === 使用增强的图片筛选逻辑 ===
        # 综合检查：文件大小、图片尺寸、内容特征
        is_filtered, filter_reason, image_info = is_low_quality_image(
            content=content,
            url=normalized_img_src,
            check_url=False,  # URL已在前面检查过
            check_dimensions=True,
            check_file_size=True,
            check_content=True,
        )
        
        if is_filtered:
            stats['skipped'] += 1
            logger.debug(f"Image filtered: {filter_reason} - {img_src[:80]}...")
            image_hash_cache[normalized_img_src] = '' if not is_multimodal else None
            return '' if not is_multimodal else None
        
        # 如果是直接图片URL嵌入模式
        # 注意：这里不再逐张做 embedding，只收集图片 URL
        # 批量 embedding 由 searxng_utils.py 统一处理，避免重复 embedding
        if use_direct_image_embedding:
            logger.debug(f"收集图片URL用于后续批量嵌入: {img_src[:50]}...")
            
            # 只返回图片URL，不做embedding，后续由searxng_utils批量处理
            result = {
                "image_url": img_src,
                "embedding_method": "deferred_batch"  # 标记为延迟批量处理
            }
            image_hash_cache[img_src] = result
            return result
                
        # 如果是多模态处理模式，在通过大小和尺寸检查后再进行多模态处理
        elif is_multimodal:
            logger.debug(f"Processing image with multimodal model: {img_src}")
            
            # 调用Qwen模型进行图片识别
            try:
                # 使用异步版本，避免阻塞事件循环，实现真正的并发处理
                result = await process_image_async(image_url=img_src)
                
                if result and isinstance(result, dict) and "describe" in result:
                    # 将图片描述添加到FAISS索引
                    description = result.get("describe", "")
                    if description and len(description) > 10:  # 确保描述有足够的内容
                        # 准备要存储的数据
                        data = {
                            "image_url": img_src,
                            "task_id": task_id,
                            "description": description
                        }
                        
                        # 添加到FAISS索引
                        try:
                            # 获取用户和文章特定的FAISS索引实例
                            logger.debug(f"正在获取FAISS索引实例: {username}/{article_id}")
                            current_faiss_index = get_streamlit_faiss_index(username=username, article_id=article_id)
                            
                            # 记录添加前的索引大小
                            before_size = current_faiss_index.get_size()
                            logger.debug(f"添加图片前FAISS索引大小: {before_size}")
                            
                            # 添加到索引
                            add_to_faiss_index(description, data, current_faiss_index, username=username, article_id=article_id, auto_save=True)
                            
                            # 记录添加后的索引大小
                            after_size = current_faiss_index.get_size()
                            logger.debug(f"添加图片后FAISS索引大小: {after_size}，增加: {after_size - before_size}")
                            
                            if after_size > before_size:
                                logger.info(f"成功添加图片到FAISS索引 {username}/{article_id}: 数量：{after_size}")
                            else:
                                logger.warning(f"图片似乎未成功添加到FAISS索引: {after_size}...")
                                
                        except Exception as e:
                            logger.error(f"添加图片到FAISS索引失败: {str(e)}")
                            logger.exception("详细错误信息:")
                    
                    # 缓存结果
                    image_hash_cache[img_src] = result
                    return result
                else:
                    logger.warning(f"Invalid or empty result from Qwen API for {img_src}")
                    image_hash_cache[img_src] = None
                    return None
            except Exception as e:
                logger.error(f"Error calling multimodal API: {str(e)}")
                image_hash_cache[img_src] = None
                return None
        
        # 计算图片内容的MD5哈希值
        content_hash = hashlib.md5(content).hexdigest()
        
        # 检查全局内容哈希映射
        global GLOBAL_CONTENT_HASH_MAPPING
        if content_hash in GLOBAL_CONTENT_HASH_MAPPING:
            # 已经有相同内容的图片
            cached_info = GLOBAL_CONTENT_HASH_MAPPING[content_hash]
            cached_path = cached_info['path']
            
            if Path(cached_path).exists():
                # 将当前URL添加到该内容哈希的URL列表中
                if normalized_img_src not in cached_info['urls']:
                    cached_info['urls'].append(normalized_img_src)
                
                # 同时为当前URL创建直接映射到路径的缓存
                image_hash_cache[normalized_img_src] = cached_path
                GLOBAL_URL_MAPPING[normalized_img_src] = {'content_hash': content_hash, 'path': cached_path}
                
                logger.debug(f"Duplicate image content detected. Using existing file: {cached_path}")
                stats['duplicate'] = stats.get('duplicate', 0) + 1
                return cached_path
                
        # 检查会话内容哈希缓存
        # 使用内容哈希作为键，值为包含文件路径和URL列表的字典
        content_hash_key = f"content_hash:{content_hash}"
        
        if content_hash_key in image_hash_cache:
            # 已经有相同内容的图片
            cached_info = image_hash_cache[content_hash_key]
            cached_path = cached_info['path']
            
            if Path(cached_path).exists():
                # 将当前URL添加到该内容哈希的URL列表中
                if normalized_img_src not in cached_info['urls']:
                    cached_info['urls'].append(normalized_img_src)
                
                # 同时为当前URL创建直接映射到路径的缓存
                image_hash_cache[normalized_img_src] = cached_path
                GLOBAL_URL_MAPPING[normalized_img_src] = {'content_hash': content_hash, 'path': cached_path}
                
                logger.debug(f"Duplicate image content detected. Using existing file: {cached_path}")
                stats['duplicate'] = stats.get('duplicate', 0) + 1
                return cached_path
        
        # 检查是否有其他文件与此内容相同（遍历一次，后续使用缓存）
        for key, value in list(image_hash_cache.items()):
            # 只检查内容哈希缓存项
            if not key.startswith("content_hash:") and isinstance(value, str) and value.startswith(str(IMAGES_DIR)) and Path(value).exists():
                try:
                    with open(value, 'rb') as f:
                        cached_content = f.read()
                        cached_hash = hashlib.md5(cached_content).hexdigest()
                        if cached_hash == content_hash:
                            # 创建内容哈希缓存项
                            image_hash_cache[content_hash_key] = {
                                'path': value,
                                'urls': [normalized_img_src, key] if key != normalized_img_src else [normalized_img_src]
                            }
                            # 为当前URL创建直接映射
                            image_hash_cache[normalized_img_src] = value
                            
                            # 更新全局映射
                            GLOBAL_URL_MAPPING[normalized_img_src] = {'content_hash': content_hash, 'path': value}
                            GLOBAL_CONTENT_HASH_MAPPING[content_hash] = {
                                'path': value,
                                'urls': [normalized_img_src]
                            }
                            
                            logger.debug(f"Duplicate image content detected. Using existing file: {value}")
                            stats['duplicate'] = stats.get('duplicate', 0) + 1
                            return value
                except Exception as e:
                    logger.warning(f"Error checking cached file {value}: {str(e)}")
        
        # 注意：图片尺寸检查已经在前面完成，这里不需要重复检查
            
        # 使用MD5哈希值作为文件名的一部分，确保唯一性
        original_filename = Path(normalized_img_src).name
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
            logger.debug(f"File with same hash already exists: {file_path}")
            
            # 创建内容哈希缓存项
            content_hash_key = f"content_hash:{content_hash}"
            if content_hash_key not in image_hash_cache:
                image_hash_cache[content_hash_key] = {
                    'path': str(file_path),
                    'urls': [normalized_img_src]
                }
            else:
                if normalized_img_src not in image_hash_cache[content_hash_key]['urls']:
                    image_hash_cache[content_hash_key]['urls'].append(normalized_img_src)
            
            # 更新全局映射
            GLOBAL_URL_MAPPING[normalized_img_src] = {'content_hash': content_hash, 'path': str(file_path)}
            GLOBAL_CONTENT_HASH_MAPPING[content_hash] = {
                'path': str(file_path),
                'urls': [normalized_img_src]
            }
            
            # 为当前URL创建直接映射
            image_hash_cache[normalized_img_src] = str(file_path)
            stats['cached'] += 1
            return str(file_path)
        
        # 保存图片 - 使用同步文件操作
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # 保存图片URL映射
        try:
            url_mapper = ImageUrlMapper(IMAGES_DIR)
            url_mapper.save_url_mapping(task_id, file_name, img_src)
            logger.debug(f"Saved URL mapping: {file_name} -> {img_src}")
        except Exception as e:
            logger.error(f"Failed to save URL mapping: {str(e)}")
            
        # 创建内容哈希缓存项
        content_hash_key = f"content_hash:{content_hash}"
        image_hash_cache[content_hash_key] = {
            'path': str(file_path),
            'urls': [normalized_img_src]
        }
        
        # 更新全局映射
        GLOBAL_URL_MAPPING[normalized_img_src] = {'content_hash': content_hash, 'path': str(file_path)}
        GLOBAL_CONTENT_HASH_MAPPING[content_hash] = {
            'path': str(file_path),
            'urls': [normalized_img_src]
        }
        
        # 为当前URL创建直接映射
        image_hash_cache[normalized_img_src] = str(file_path)
        stats['success'] += 1
        return str(file_path)
        
    except Exception as e:
        stats['failed'] += 1
        image_hash_cache[normalized_img_src] = ''
        return ''

def normalize_image_url(img_src: str, base_url: str = None) -> str:
    """
    规范化图片URL，处理相对路径和特殊情况
    
    Args:
        img_src: 图片URL或路径
        base_url: 页面基础URL，用于解析相对路径
        
    Returns:
        规范化后的完整URL，如果无法解析则返回空字符串
    """
    if not img_src or img_src.strip() == '':
        return ''
        
    # 跳过数据URL
    if img_src.startswith('data:'):
        return ''
    
    # 处理特殊URL格式
    img_src = img_src.strip()
    
    # 修复一些常见的URL格式问题
    img_src = img_src.replace('\\', '/')
    
    # 处理URL中的空格和特殊字符
    try:
        # 解析URL组件
        parsed = urllib.parse.urlparse(img_src)
        
        # 如果路径部分包含空格或特殊字符，进行编码
        if parsed.path and (' ' in parsed.path or '%' not in parsed.path and any(c in parsed.path for c in '#?&=+[]{}|\\^~`<>')):
            path_parts = parsed.path.split('/')
            encoded_path = '/'.join(urllib.parse.quote(part) for part in path_parts)
            
            # 重新构建URL
            img_src = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, encoded_path, 
                                            parsed.params, parsed.query, parsed.fragment))
    except Exception as e:
        logger.debug(f"Error normalizing URL {img_src}: {str(e)}")
    
    # 处理相对路径
    if img_src.startswith('//'):
        # 协议相对URL
        return f"https:{img_src}"
    elif img_src.startswith('/'):
        # 网站根相对路径
        if base_url:
            try:
                return urllib.parse.urljoin(base_url, img_src)
            except Exception as e:
                logger.warning(f"Error joining URL {base_url} with {img_src}: {str(e)}")
                # 尝试从base_url提取域名
                try:
                    parsed = urllib.parse.urlparse(base_url)
                    return f"{parsed.scheme}://{parsed.netloc}{img_src}"
                except:
                    return ''
        else:
            return ''
    elif not img_src.startswith(('http://', 'https://')):
        # 其他相对路径
        if base_url:
            try:
                return urllib.parse.urljoin(base_url, img_src)
            except Exception as e:
                logger.warning(f"Error joining URL {base_url} with {img_src}: {str(e)}")
                return ''
        else:
            return ''
            
    # 处理特殊CDN URL
    # 网易图片URL处理
    if 'nimg.ws.126.net' in img_src or '126.net' in img_src:
        if 'url=' in img_src:
            try:
                parsed_url = urllib.parse.urlparse(img_src)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if 'url' in query_params:
                    actual_img_url = query_params['url'][0]
                    return actual_img_url
            except Exception:
                pass
                
    # 处理新浪微博图片URL
    if 'sinaimg.cn' in img_src:
        # 尝试获取原图而不是缩略图
        try:
            if '/thumb' in img_src:
                return img_src.replace('/thumb', '/large')
            elif '/small' in img_src:
                return img_src.replace('/small', '/large')
            elif '/mw690' in img_src:
                return img_src.replace('/mw690', '/large')
        except:
            pass
            
    # 处理百度图片URL
    if 'bdimg.com' in img_src or 'bdstatic.com' in img_src:
        # 尝试处理百度的图片URL
        try:
            if '&src=' in img_src:
                parsed_url = urllib.parse.urlparse(img_src)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if 'src' in query_params:
                    actual_img_url = query_params['src'][0]
                    return urllib.parse.unquote(actual_img_url)
        except:
            pass
            
    # 处理政府网站图片URL
    if 'gov.cn' in img_src:
        # 尝试处理政府网站的图片URL
        try:
            # 移除可能导致问题的查询参数
            if '?' in img_src:
                parsed_url = urllib.parse.urlparse(img_src)
                # 如果查询参数中包含v=，可能是版本或缓存控制，尝试移除
                if 'v=' in parsed_url.query:
                    clean_url = urllib.parse.urlunparse((parsed_url.scheme, parsed_url.netloc, 
                                                       parsed_url.path, '', '', ''))
                    logger.debug(f"Cleaned gov.cn URL: {img_src} -> {clean_url}")
                    return clean_url
        except:
            pass
            
    # 处理中国日报网站图片URL
    if 'chinadaily.com.cn' in img_src:
        try:
            # 检查是否有特定的查询参数或路径模式
            if '_ORIGIN' in img_src:
                # 尝试移除_ORIGIN后缀，获取原始图片
                clean_url = img_src.replace('_ORIGIN', '')
                logger.debug(f"Cleaned chinadaily URL: {img_src} -> {clean_url}")
                return clean_url
        except:
            pass
            
    return img_src

async def text_from_html(body: str, session: aiohttp.ClientSession, task_id: str, is_multimodal: bool = False, use_direct_image_embedding: bool = False, theme: str = "", page_url: str = None, username: str = None, article_id: str = None) -> Dict[str, any]:
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
        processed_paths = []  # Initialize processed_paths here to ensure it's always defined
        
        if img_tags:
            # 创建一个字典来存储图片哈希和路径
            image_hash_cache = {}
            
            # 创建异步任务列表
            img_tasks = []
            base_url = None
            
            # 尝试提取基础URL，用于解析相对路径
            try:
                # 首先使用传入的页面URL
                if page_url:
                    base_url = page_url
                else:
                    # 从页面中提取基础URL
                    base_tag = soup.find('base', href=True)
                    if base_tag and base_tag.get('href'):
                        base_url = base_tag['href']
                    else:
                        # 尝试从meta标签中提取URL
                        meta_url = None
                        for meta in soup.find_all('meta', property=['og:url', 'twitter:url']):
                            meta_url = meta.get('content')
                            if meta_url:
                                base_url = meta_url
                                break
                        
                        # 尝试从canonical链接中提取
                        if not base_url:
                            canonical = soup.find('link', rel='canonical')
                            if canonical and canonical.get('href'):
                                base_url = canonical.get('href')
                                
                        # 尝试从页面头部提取
                        if not base_url:
                            head_links = soup.find_all('link')
                            for link in head_links:
                                if link.get('rel') and 'stylesheet' in link.get('rel') and link.get('href'):
                                    href = link.get('href')
                                    if href.startswith('http'):
                                        parsed = urllib.parse.urlparse(href)
                                        base_url = f"{parsed.scheme}://{parsed.netloc}"
                                        break
            except Exception as e:
                logger.warning(f"Error extracting base URL: {str(e)}")
                
            # 收集更全面的图片URL来源
            img_src_candidates = []

            # 1) 常规 <img> 标签
            for img in img_tags:
                candidates = set()

                # src
                val = (img.get('src') or '').strip()
                if val:
                    candidates.add(val)

                # 常见的懒加载与自定义属性
                for attr in ['data-src', 'data-original', 'data-actualsrc', 'data-orig-src', 'data-lazy-src', 'data-image', 'data-url']:
                    v = (img.get(attr) or '').strip()
                    if v:
                        candidates.add(v)

                # srcset（选择最大分辨率或最后一个）
                srcset = (img.get('srcset') or '').strip()
                if srcset:
                    try:
                        parts = [p.strip() for p in srcset.split(',') if p.strip()]
                        # 提取 (url, descriptor)，优先包含 'w' 的最大，否则取最后一个
                        parsed = []
                        for p in parts:
                            seg = p.split()
                            if len(seg) >= 1:
                                url = seg[0]
                                desc = seg[1] if len(seg) > 1 else ''
                                parsed.append((url, desc))
                        # 选择最大 w 值
                        best = None
                        maxw = -1
                        for url, desc in parsed:
                            if desc.endswith('w'):
                                try:
                                    w = int(desc[:-1])
                                    if w > maxw:
                                        maxw = w
                                        best = url
                                except:
                                    pass
                        if not best and parsed:
                            best = parsed[-1][0]
                        if best:
                            candidates.add(best)
                    except Exception:
                        pass

                # 父级 <a> 可能直接链接图片
                parent = img.parent
                if parent and getattr(parent, 'name', '').lower() == 'a':
                    href = (parent.get('href') or '').strip()
                    if href and any(href.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
                        candidates.add(href)

                # 去重后加入全局候选
                for c in candidates:
                    img_src_candidates.append(c)

            # 2) <picture> 中的 <source srcset>
            for picture in soup.find_all('picture'):
                for source in picture.find_all('source'):
                    srcset = (source.get('srcset') or '').strip()
                    if srcset:
                        try:
                            parts = [p.strip() for p in srcset.split(',') if p.strip()]
                            for p in parts:
                                url = p.split()[0]
                                if url:
                                    img_src_candidates.append(url)
                        except Exception:
                            pass

            # 3) CSS 背景图片 url(...) 提取
            for elem in soup.find_all(style=True):
                style = elem.get('style') or ''
                # 简单提取 url('...') / url("...") / url(...)
                urls = re.findall(r"url\((?:'|\")?(.*?)(?:'|\")?\)", style)
                for u in urls:
                    if u:
                        img_src_candidates.append(u)

            # 去重
            unique_candidates = []
            seen = set()
            for u in img_src_candidates:
                if not u:
                    continue
                if u in seen:
                    continue
                seen.add(u)
                unique_candidates.append(u)

            # 初始化统计字典（以候选URL数为准）
            stats = {
                'total': len(unique_candidates),
                'success': 0,
                'failed': 0,
                'cached': 0,
                'skipped': 0
            }

            # 创建下载/处理任务
            for candidate in unique_candidates:
                task = download_image(session, candidate, image_hash_cache, task_id, is_multimodal, use_direct_image_embedding, theme, stats, base_url, username, article_id)
                img_tasks.append(task)
            
            # 等待所有图片下载完成，设置整体超时（30秒）
            try:
                img_paths = await asyncio.wait_for(
                    asyncio.gather(*img_tasks, return_exceptions=True),
                    timeout=30
                )
                # 过滤掉异常结果
                img_paths = [p for p in img_paths if not isinstance(p, Exception)]
            except asyncio.TimeoutError:
                logger.warning(f"图片下载超时，已处理部分图片")
                img_paths = []
            
            # 处理直接嵌入模式下的字典结果
            processed_paths = []
            for path in img_paths:
                if path:
                    if isinstance(path, dict) and 'image_url' in path:
                        # 如果是直接嵌入模式下的字典结果，提取URL
                        processed_paths.append(path['image_url'])
                    else:
                        # 普通字符串路径
                        processed_paths.append(path)
            
            # 输出图片下载统计信息
            logger.debug(f"图片下载统计: 总计 {stats['total']} 张, 成功 {stats['success']} 张, 失败 {stats['failed']} 张, 使用缓存 {stats['cached']} 张, 跳过 {stats['skipped']} 张, 去重 {stats.get('duplicate', 0)} 张")
            
            # 输出全局缓存统计信息
            logger.debug(f"全局URL映射缓存大小: {len(GLOBAL_URL_MAPPING)}, 全局内容哈希映射大小: {len(GLOBAL_CONTENT_HASH_MAPPING)}")
        
        return {
            'text': text_content,
            'images': processed_paths
        }
        
    except Exception as e:
        logger.error(f"Error processing HTML content: {str(e)}")
        return {'text': '', 'images': []}

async def fetch(browser, url, task_id=None, is_multimodal=False, use_direct_image_embedding=False, theme="", username=None, article_id=None) -> Dict[str, any]:
    """
    获取页面内容
    """
    # 早期检查：跳过空URL
    if not url or not url.strip():
        logger.warning("Skipping empty URL")
        return {"url": url, "text": "", "images": [], "error": "Empty URL"}
    
    logger.debug(f"开始抓取URL: {url[:80]}...")
    
    async with aiohttp.ClientSession() as session:
        # 创建一个新的浏览器上下文
        try:
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},  # 更大的视口以加载更多内容
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            # 创建一个新页面
            page = await context.new_page()
            
            # 设置请求拦截器，允许所有请求通过
            await page.route("**/*", lambda route: route.continue_())
            
            # 访问 URL，并等待完成所有重定向
            # 使用 domcontentloaded 而不是 networkidle，因为很多网站有持续的网络请求导致 networkidle 永远不会触发
            timeout = 30000  # 固定超时时间，毫秒
            try:
                response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                # 尝试等待 networkidle，但设置较短超时
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    # networkidle 超时不是致命错误，继续处理
                    logger.debug(f"networkidle timeout for {url}, continuing with domcontentloaded")
            except Exception as goto_error:
                # 如果 domcontentloaded 也失败，尝试使用 commit （最快的等待策略）
                logger.warning(f"domcontentloaded failed for {url}: {goto_error}, trying with commit")
                response = await page.goto(url, timeout=timeout, wait_until="commit")
            
            # 获取最终 URL（重定向后）
            final_url = page.url
            
            if final_url != url:
                logger.debug(f"URL redirected: {url} -> {final_url}")
                
            # 等待页面完全加载，包括动态内容
            await asyncio.sleep(2)  # 给JavaScript一些时间来加载内容
            
            # 尝试滚动页面以加载懒加载图片
            try:
                await page.evaluate("""
                    async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 300;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                
                                if(totalHeight >= scrollHeight){
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                        });
                    }
                """)
                await asyncio.sleep(1)  # 给懒加载图片一些时间来加载
            except Exception as scroll_error:
                logger.warning(f"Error during page scrolling: {str(scroll_error)}")
            
            # 获取页面内容
            content = await page.content()
            
            # 处理页面内容
            result = await text_from_html(content, session, task_id, is_multimodal, use_direct_image_embedding, theme, final_url, username, article_id)  # 使用最终URL，传递用户名和文章ID
            result['url'] = final_url  # 使用最终URL而不是原始URL
            result['original_url'] = url  # 保存原始URL以便跟踪
            return result
        except Exception as e:
            error_message = str(e)
            # 过滤掉PDF下载的错误日志
            if "Download is starting" in error_message:
                # 对于PDF下载，使用debug级别记录，而不是error
                logger.debug(f"Skipping PDF download for {url}: {error_message}")
            else:
                # 其他错误仍然使用error级别记录
                logger.error(f"Error fetching {url}: {error_message}")
            return {"url": url, "text": "", "images": [], "error": error_message}
        finally:
            await page.close()
            await context.close()

async def get_main_content(url_list: List[str], task_id: str = None, is_multimodal: bool = False, use_direct_image_embedding: bool = False, theme: str = "", progress_callback: Optional[callable] = None, username: str = None, article_id: str = None) -> List[Dict[str, any]]:
    """
    获取多个URL的内容，并提供进度回调
    :param url_list: URL列表
    :param task_id: 任务ID，如果未提供则使用时间戳
    :param progress_callback: 进度回调函数，接收 (completed_count, total_count)
    """
    get_executor()
    
    logger.info(f"开始抓取 {len(url_list)} 个URL的内容...")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch()
        try:
            if task_id is None:
                task_id = f"task_{int(asyncio.get_event_loop().time())}"
            
            tasks = [fetch(browser, url, task_id, is_multimodal=is_multimodal, use_direct_image_embedding=use_direct_image_embedding, theme=theme, username=username, article_id=article_id) for url in url_list]
            
            results = []
            completed_count = 0
            total_count = len(tasks)
            
            # 设置单个任务的超时时间（秒）
            TASK_TIMEOUT = 60

            for future in asyncio.as_completed(tasks):
                try:
                    # 为每个任务设置超时
                    result = await asyncio.wait_for(future, timeout=TASK_TIMEOUT)
                    results.append(result)
                    completed_count += 1
                    logger.info(f"抓取进度: {completed_count}/{total_count} - URL: {result.get('url', 'unknown')[:50]}...")
                except asyncio.TimeoutError:
                    completed_count += 1
                    logger.warning(f"抓取超时 ({TASK_TIMEOUT}s): 任务 {completed_count}/{total_count}")
                    results.append({"url": "timeout", "text": "", "images": [], "error": "timeout"})
                except Exception as e:
                    completed_count += 1
                    logger.error(f"抓取异常: {str(e)}")
                    results.append({"url": "error", "text": "", "images": [], "error": str(e)})
                
                if progress_callback:
                    try:
                        progress_callback(completed_count, total_count)
                    except Exception as e:
                        logger.error(f"Error in progress_callback: {e}")

            logger.info(f"抓取完成: 成功 {len([r for r in results if r.get('text')])} / 总计 {total_count}")
            return results, task_id
        finally:
            await asyncio.sleep(0.5)
            await browser.close()

if __name__ == '__main__':
    url_list = ['http://news.china.com.cn/2024-11/18/content_117554263.shtml']
    try:
        main_content = asyncio.run(get_main_content(url_list, task_id="test_task"))
        if main_content:
            print(main_content)
        else:
            print("Failed to retrieve the main content.")
    finally:
        # 确保在程序退出前关闭executor
        shutdown_executor()