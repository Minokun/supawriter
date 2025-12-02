"""
图片筛选工具 - 用于过滤低质量、非内容相关的图片

筛选维度：
1. 尺寸筛选 - 过滤太小或比例异常的图片
2. 文件大小筛选 - 过滤文件太小的图片
3. URL特征筛选 - 过滤logo、图标、广告等非内容图片
4. 图片内容特征筛选 - 基于图片本身的特征判断
"""

import re
import logging
from typing import Optional, Tuple, Dict, List
from urllib.parse import urlparse, parse_qs
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


# ============== 配置参数 ==============

# 最小图片尺寸要求 - 更严格的阈值
MIN_WIDTH = 300   # 最小宽度 - 提高到300
MIN_HEIGHT = 200  # 最小高度 - 提高到200
MIN_AREA = 80000  # 最小面积 (宽*高) - 提高到80000

# 文件大小限制
MIN_FILE_SIZE = 15 * 1024  # 最小文件大小 15KB - 提高阈值
MAX_FILE_SIZE = 20 * 1024 * 1024  # 最大文件大小 20MB

# 宽高比限制 - 更严格
MIN_ASPECT_RATIO = 0.2   # 最小宽高比 (允许竖长图但不能太极端)
MAX_ASPECT_RATIO = 5.0   # 最大宽高比 (允许横幅但不能太极端)

# 常见图标尺寸（精确匹配）- 扩展列表
ICON_SIZES = {
    (16, 16), (24, 24), (32, 32), (36, 36), (48, 48),
    (64, 64), (72, 72), (96, 96), (128, 128), (144, 144),
    (152, 152), (180, 180), (192, 192), (256, 256),
    (300, 300), (480, 480), (512, 512),
    (226, 226), (656, 656),
    (57, 57), (60, 60), (70, 70), (76, 76), (114, 114),
    (120, 120), (150, 150), (167, 167),
    # 更多常见尺寸
    (100, 100), (200, 200), (400, 400), (600, 600),
    (40, 40), (50, 50), (80, 80), (90, 90),
    (20, 20), (28, 28), (44, 44), (56, 56),
}

# 近似正方形图标的尺寸范围 - 扩大范围
ICON_SIZE_RANGE = (10, 400)  # 10-400px 范围内的近似正方形可能是图标


# ============== URL 特征黑名单 ==============

# Logo/图标相关的URL关键词 - 更宽松的匹配（不要求特定位置）
# 注意：这些关键词会匹配URL路径中的任意位置，所以要谨慎添加
# 避免添加可能出现在正常内容图片路径中的词（如 upload, image, photo 等）
LOGO_ICON_KEYWORDS = [
    # 明确的图标/logo标识
    'logo', 'icon', 'favicon', 'brand', 'sprite', 'avatar',
    'badge', 'emoji', 'emoticon', 'sticker',
    # 缩略图/小图标识
    'thumb_', 'thumbnail_', '_thumb', '_thumbnail',
    'mini_', 'small_', 'tiny_', '_mini', '_small', '_tiny',
    # 二维码/条形码
    'qrcode', 'qr-code', 'qr_code', 'barcode',
    # 水印/占位符
    'watermark', 'placeholder', 'loading', 'spinner',
    # UI元素
    'arrow_', 'button_', 'btn_', 'nav_', 'menu_',
    '_arrow', '_button', '_btn', '_nav', '_menu',
    'header_icon', 'footer_icon', 'sidebar_icon',
    'widget_', '_widget',
    # 社交分享图标
    'social_', 'share_', 'follow_', 'like_', 'comment_',
    '_social', '_share', '_follow', '_like', '_comment',
    # 评分/装饰元素
    'rating_', 'star_', 'dot_', 'bullet_', 'divider_',
    '_rating', '_star', '_dot', '_bullet', '_divider',
    'separator_', '_separator',
    # 背景/纹理（作为文件名的一部分）
    'bg_', 'bg-', '_bg.', '-bg.',
    'background_', 'background-', '_background.', '-background.',
    'pattern_', 'texture_', 'gradient_',
    # 默认/空白图片
    'default_', 'blank_', 'empty_', 'spacer_', 'pixel_',
    '_default', '_blank', '_empty', '_spacer', '_pixel',
    '1x1', 'transparent_', 'clear_',
    'noimage', 'no-image', 'no_image', 'missing_',
    'anonymous_', 'default-avatar', 'default_avatar',
    # 社交媒体图标（作为文件名）
    'wechat_icon', 'weixin_icon', 'weibo_icon',
    'twitter_icon', 'facebook_icon', 'instagram_icon',
    'youtube_icon', 'tiktok_icon',
    'app_store_', 'google_play_',
    # 操作图标
    'close_', 'open_', 'expand_', 'collapse_',
    'check_', 'tick_', 'cross_', 'plus_', 'minus_',
    'add_', 'remove_', 'edit_', 'delete_', 'trash_',
    'search_', 'zoom_', 'play_', 'pause_', 'stop_',
    'next_', 'prev_', 'forward_', 'back_', 'home_',
    '_close', '_open', '_expand', '_collapse',
    '_check', '_tick', '_cross', '_plus', '_minus',
    # 用户/设置图标
    'user_icon', 'profile_icon', 'setting_icon', 'config_icon',
    'gear_', 'cog_', 'tool_',
    # 通知/状态图标
    'info_', 'help_', 'question_', 'warning_', 'error_', 'success_',
    'notification_', 'bell_', 'mail_', 'email_', 'phone_', 'call_',
    # 其他UI图标
    'chat_', 'message_', 'send_', 'attach_', 'link_',
    'copy_', 'paste_', 'undo_', 'redo_', 'refresh_', 'reload_',
    'sync_', 'cloud_icon', 'file_icon', 'folder_icon',
    'calendar_', 'clock_', 'location_', 'map_', 'pin_', 'marker_',
    'flag_', 'bookmark_', 'heart_', 'love_',
    'thumbup', 'thumbdown', 'smile_icon', 'sad_icon',
]

# 广告/跟踪相关的域名
AD_TRACKING_DOMAINS = [
    'googleads', 'googlesyndication', 'doubleclick',
    'adservice', 'adsrvr', 'adnxs', 'advertising',
    'scorecardresearch', 'amazon-adsystem', 'moatads',
    'taboola', 'outbrain', 'criteo', 'pubmatic',
    'rubiconproject', 'openx', 'appnexus', 'spotxchange',
    'sharethrough', 'teads', 'triplelift', 'indexexchange',
    'bidswitch', 'casalemedia', 'contextweb', 'yieldmo',
    'kunyu.csdn.net', 'ad.csdn.net', 'ads.csdn.net',
    'beacon', 'tracker', 'tracking', 'pixel', 'analytics',
    'stat.', 'stats.', 'count.', 'counter.',
    # 更多广告域名
    'adskeeper', 'adsterra', 'propellerads', 'mgid',
    'revcontent', 'content.ad', 'zergnet', 'nativo',
]

# 广告相关的URL路径关键词 - 使用更精确的模式避免误匹配
# 例如 'upload' 包含 'ad'，所以需要用边界匹配
AD_PATH_KEYWORDS = [
    '/ads/', '/ad/', '/advert/', '/banner/', '/promo/', '/sponsor/',
    '/affiliate/', '/tracking/', '/beacon/', '/pixel/', '/impression/',
    '/campaign/', '/analytics/',
    '_ads_', '_ad_', '-ads-', '-ad-',
    'ads.', 'ad.', 'advert.', 'banner.', 'promo.',
]

# 静态资源/UI元素域名 - 这些域名通常托管UI图标而非内容图片
STATIC_ASSET_DOMAINS = [
    'static.', 'assets.', 'cdn.', 'res.', 'resource.',
    's3.', 'storage.', 'media.', 'img.', 'images.',
    # 特定网站的静态资源域名
    'g.csdnimg.cn',  # CSDN 静态资源（通常是UI元素）
]

# 需要保留的内容图片域名关键词（白名单）
CONTENT_IMAGE_DOMAINS = [
    'img-blog', 'article', 'content', 'post', 'news',
    'photo', 'picture', 'upload', 'user-images',
]

# 社交媒体图标域名
SOCIAL_ICON_DOMAINS = [
    'platform-lookaside.fbsbx.com',  # Facebook
    'abs.twimg.com',  # Twitter
    'static.licdn.com',  # LinkedIn
    'static.xx.fbcdn.net',  # Facebook static
]


# ============== 筛选函数 ==============

def is_likely_logo_or_icon_by_url(url: str) -> Tuple[bool, str]:
    """
    通过URL特征判断是否可能是logo或图标
    使用更宽松的关键词匹配
    
    Returns:
        (is_filtered, reason)
    """
    if not url:
        return True, "empty_url"
    
    url_lower = url.lower()
    parsed = urlparse(url_lower)
    path = parsed.path
    domain = parsed.netloc
    
    # 先检查白名单 - 如果是内容图片域名，直接放行
    for content_domain in CONTENT_IMAGE_DOMAINS:
        if content_domain in domain:
            return False, ""
    
    # 检查域名是否为广告/跟踪域名
    for ad_domain in AD_TRACKING_DOMAINS:
        if ad_domain in domain:
            return True, f"ad_domain:{ad_domain}"
    
    # 检查是否为社交媒体图标域名
    for social_domain in SOCIAL_ICON_DOMAINS:
        if social_domain in domain:
            return True, f"social_icon_domain:{social_domain}"
    
    # 提取文件名（不含扩展名）
    filename = path.split('/')[-1].lower() if path else ''
    filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # 检查URL路径和文件名是否包含logo/icon相关关键词
    # 使用更宽松的匹配：只要包含关键词就过滤
    url_to_check = path + '/' + filename_no_ext
    for keyword in LOGO_ICON_KEYWORDS:
        if keyword in url_to_check:
            return True, f"keyword:{keyword}"
    
    # 检查广告路径关键词
    for keyword in AD_PATH_KEYWORDS:
        if keyword in url_to_check:
            return True, f"ad_keyword:{keyword}"
    
    # 检查URL查询参数中的广告标识
    query_params = parse_qs(parsed.query)
    ad_params = ['adid', 'ad_id', 'adblockflag', 'ad_block', 'utm_', 'track']
    for param in query_params:
        for ad_param in ad_params:
            if ad_param in param.lower():
                return True, f"ad_query_param:{param}"
    
    # 检查是否为 data URI (base64 编码的小图片通常是图标)
    if url_lower.startswith('data:'):
        # 检查 data URI 的大小，太小的可能是图标
        if len(url) < 5000:  # 约 3-4KB 的 base64 数据
            return True, "small_data_uri"
    
    return False, ""


def is_likely_icon_by_dimensions(width: int, height: int) -> Tuple[bool, str]:
    """
    通过图片尺寸判断是否可能是图标
    
    Returns:
        (is_filtered, reason)
    """
    # 精确匹配常见图标尺寸
    if (width, height) in ICON_SIZES:
        return True, f"exact_icon_size:{width}x{height}"
    
    # 检查是否为近似正方形且在图标尺寸范围内
    if ICON_SIZE_RANGE[0] <= width <= ICON_SIZE_RANGE[1]:
        if ICON_SIZE_RANGE[0] <= height <= ICON_SIZE_RANGE[1]:
            # 计算宽高比
            ratio = width / height if height > 0 else 0
            # 近似正方形 (0.9 - 1.1)
            if 0.9 <= ratio <= 1.1:
                return True, f"square_icon_range:{width}x{height}"
    
    # 检查是否太小
    if width < MIN_WIDTH and height < MIN_HEIGHT:
        return True, f"too_small:{width}x{height}"
    
    # 检查面积是否太小
    area = width * height
    if area < MIN_AREA:
        return True, f"small_area:{area}"
    
    # 检查宽高比是否异常
    if height > 0:
        ratio = width / height
        if ratio < MIN_ASPECT_RATIO:
            return True, f"narrow_vertical:{ratio:.2f}"
        if ratio > MAX_ASPECT_RATIO:
            return True, f"wide_horizontal:{ratio:.2f}"
    
    return False, ""


def is_low_quality_image(
    content: bytes,
    url: str = "",
    check_url: bool = True,
    check_dimensions: bool = True,
    check_file_size: bool = True,
    check_content: bool = True,
) -> Tuple[bool, str, Optional[Dict]]:
    """
    综合判断图片是否为低质量/非内容图片
    
    Args:
        content: 图片二进制内容
        url: 图片URL
        check_url: 是否检查URL特征
        check_dimensions: 是否检查尺寸
        check_file_size: 是否检查文件大小
        check_content: 是否检查图片内容特征
    
    Returns:
        (is_filtered, reason, image_info)
        - is_filtered: 是否应该被过滤
        - reason: 过滤原因
        - image_info: 图片信息字典 (width, height, format, etc.)
    """
    image_info = {}
    
    # 1. URL 特征检查
    if check_url and url:
        is_filtered, reason = is_likely_logo_or_icon_by_url(url)
        if is_filtered:
            logger.debug(f"Image filtered by URL: {reason} - {url[:100]}")
            return True, f"url:{reason}", image_info
    
    # 2. 文件大小检查
    if check_file_size:
        file_size = len(content)
        image_info['file_size'] = file_size
        
        if file_size < MIN_FILE_SIZE:
            logger.debug(f"Image filtered by file size: {file_size} bytes < {MIN_FILE_SIZE} bytes")
            return True, f"file_too_small:{file_size}", image_info
        
        if file_size > MAX_FILE_SIZE:
            logger.debug(f"Image filtered by file size: {file_size} bytes > {MAX_FILE_SIZE} bytes")
            return True, f"file_too_large:{file_size}", image_info
    
    # 3. 图片尺寸和内容检查
    if (check_dimensions or check_content) and Image:
        try:
            img = Image.open(BytesIO(content))
            width, height = img.size
            image_info['width'] = width
            image_info['height'] = height
            image_info['format'] = img.format
            image_info['mode'] = img.mode
            
            # 尺寸检查
            if check_dimensions:
                is_filtered, reason = is_likely_icon_by_dimensions(width, height)
                if is_filtered:
                    logger.debug(f"Image filtered by dimensions: {reason}")
                    return True, f"dimensions:{reason}", image_info
            
            # 内容特征检查
            if check_content:
                # 检查是否为纯色或近似纯色图片
                is_filtered, reason = _check_image_content(img)
                if is_filtered:
                    logger.debug(f"Image filtered by content: {reason}")
                    return True, f"content:{reason}", image_info
                    
        except Exception as e:
            logger.debug(f"Failed to analyze image: {e}")
            # 无法解析的图片不一定要过滤，可能是特殊格式
            image_info['parse_error'] = str(e)
    
    return False, "", image_info


def _check_image_content(img: 'Image.Image') -> Tuple[bool, str]:
    """
    检查图片内容特征
    
    Returns:
        (is_filtered, reason)
    """
    try:
        # 转换为 RGB 模式进行分析
        if img.mode != 'RGB':
            if img.mode == 'RGBA':
                # 检查透明度 - 大量透明像素可能是图标
                alpha = img.split()[-1]
                alpha_data = list(alpha.getdata())
                transparent_ratio = sum(1 for a in alpha_data if a < 128) / len(alpha_data)
                if transparent_ratio > 0.7:  # 70% 以上透明
                    return True, f"high_transparency:{transparent_ratio:.2f}"
            
            # 转换为 RGB
            try:
                img = img.convert('RGB')
            except Exception:
                return False, ""
        
        # 缩小图片进行快速分析
        thumb_size = (50, 50)
        thumb = img.resize(thumb_size, Image.Resampling.LANCZOS)
        pixels = list(thumb.getdata())
        
        # 计算颜色多样性
        unique_colors = len(set(pixels))
        total_pixels = len(pixels)
        color_diversity = unique_colors / total_pixels
        
        # 颜色多样性太低可能是纯色背景或简单图形
        if color_diversity < 0.05:  # 少于 5% 的颜色多样性
            return True, f"low_color_diversity:{color_diversity:.3f}"
        
        # 检查是否为灰度图（可能是占位符）
        is_grayscale = all(
            abs(r - g) < 10 and abs(g - b) < 10 and abs(r - b) < 10
            for r, g, b in pixels
        )
        if is_grayscale and color_diversity < 0.1:
            return True, "grayscale_low_diversity"
        
    except Exception as e:
        logger.debug(f"Error checking image content: {e}")
    
    return False, ""


def filter_image_urls(
    urls: List[str],
    check_url_only: bool = True
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    批量过滤图片URL列表
    
    Args:
        urls: URL列表
        check_url_only: 是否只检查URL（不下载图片内容）
    
    Returns:
        (valid_urls, filtered_urls_with_reasons)
    """
    valid_urls = []
    filtered = []
    
    for url in urls:
        if check_url_only:
            is_filtered, reason = is_likely_logo_or_icon_by_url(url)
            if is_filtered:
                filtered.append((url, reason))
            else:
                valid_urls.append(url)
        else:
            valid_urls.append(url)
    
    if filtered:
        logger.info(f"URL pre-filter: {len(filtered)} images filtered, {len(valid_urls)} remaining")
    
    return valid_urls, filtered


def get_filter_stats(filtered_reasons: List[str]) -> Dict[str, int]:
    """
    统计过滤原因分布
    
    Args:
        filtered_reasons: 过滤原因列表
    
    Returns:
        原因分类统计字典
    """
    stats = {}
    for reason in filtered_reasons:
        # 提取主要原因类别
        category = reason.split(':')[0] if ':' in reason else reason
        stats[category] = stats.get(category, 0) + 1
    return stats


# ============== 便捷函数 ==============

def should_skip_image_url(url: str) -> bool:
    """
    快速判断是否应该跳过该图片URL
    
    这是一个便捷函数，用于在下载前快速过滤明显的非内容图片
    """
    is_filtered, _ = is_likely_logo_or_icon_by_url(url)
    return is_filtered


def should_skip_image(
    content: bytes,
    url: str = "",
    width: int = 0,
    height: int = 0
) -> Tuple[bool, str]:
    """
    综合判断是否应该跳过该图片
    
    这是一个便捷函数，整合了所有检查逻辑
    
    Returns:
        (should_skip, reason)
    """
    # 如果提供了尺寸信息，先检查尺寸
    if width > 0 and height > 0:
        is_filtered, reason = is_likely_icon_by_dimensions(width, height)
        if is_filtered:
            return True, reason
    
    # 综合检查
    is_filtered, reason, _ = is_low_quality_image(content, url)
    return is_filtered, reason
