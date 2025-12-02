"""
Utilities for ensuring blog images are publicly accessible by re-hosting
Baidu/CDN-protected URLs to Qiniu Cloud.

- Reads credentials from Streamlit secrets:
  QINIU_Domain, QINIU_Folder, QINIU_Accesskey, QINIU_SecretKey
- Uses bucket name fixed to "source" as provided by the user.
- Public URL format: QINIU_Domain + QINIU_Folder + <uploaded-filename>

The upload key is deterministic based on the source URL hash to avoid duplicates.
Will gracefully fall back to the original URL on any error.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional
from urllib.parse import urlparse

import requests

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # Fallback when not running under Streamlit

logger = logging.getLogger(__name__)


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().strip()


def _get_secrets(key: str, default: Optional[str] = None) -> Optional[str]:
    # Prefer environment variable override first (safe in any thread)
    env_val = os.getenv(key)
    if env_val is not None:
        return env_val

    # Access Streamlit secrets only when a ScriptRunContext exists to avoid
    # "missing ScriptRunContext" warnings from worker threads
    if st is not None:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
            if get_script_run_ctx() is not None:
                return st.secrets.get(key, default)
            # No ScriptRunContext: skip touching st.secrets to avoid warning
            return default
        except Exception:
            return default

    # Fallback when Streamlit isn't available
    return default


def _normalize_folder(folder: Optional[str]) -> str:
    if not folder:
        return ""
    # Ensure single trailing slash or empty
    folder = folder.strip()
    if not folder:
        return ""
    if not folder.endswith('/'):
        folder = folder + '/'
    return folder


# Basic heuristic for protected CDN sources (focus on Baidu/CDN)
PROTECTED_HOST_KEYWORDS = [
    'baidu', 'bdstatic', 'bdimg', 'hiphotos', 'tiebapic', 'wkimg', 'baidupcs', 'cdn'
]


def is_protected_cdn_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ''
        host = host.lower()
        return any(k in host for k in PROTECTED_HOST_KEYWORDS)
    except Exception:
        return False


def _guess_ext_from_url(url: str) -> str:
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    ext = (ext or '').lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return ext
    return '.jpg'


def _make_upload_token(access_key: str, secret_key: str, bucket: str, key: str, expires: int = 3600) -> str:
    # Qiniu upload policy
    put_policy = {
        'scope': f'{bucket}:{key}',
        'deadline': int(time.time()) + expires,
    }
    policy = json.dumps(put_policy, separators=(',', ':')).encode()
    encoded_policy = _urlsafe_b64encode(policy)
    sign = hmac.new(secret_key.encode(), encoded_policy.encode(), hashlib.sha1).digest()
    encoded_sign = _urlsafe_b64encode(sign)
    return f"{access_key}:{encoded_sign}:{encoded_policy}"


def _host_for_region(region: Optional[str]) -> str:
    """Map Qiniu region code to upload host. Defaults to z2 if not set."""
    mapping = {
        'z0': 'upload.qiniup.com',          # East China
        'z1': 'upload-z1.qiniup.com',       # North China
        'z2': 'up-z2.qiniup.com',           # South China
        'na0': 'upload-na0.qiniup.com',     # North America
        'as0': 'upload-as0.qiniup.com',     # Southeast Asia
    }
    r = (region or '').strip().lower()
    return mapping.get(r, 'up-z2.qiniup.com')  # default to z2 per user's environment


def _deterministic_key(url: str, ext: str, folder: str) -> str:
    sha = hashlib.sha1(url.encode()).hexdigest()[:16]
    return f"{folder}{sha}{ext}"


def upload_image_from_url(image_url: str) -> Optional[str]:
    """
    Upload an image fetched from a URL to Qiniu and return its public URL.
    Returns None on failure.
    """
    try:
        # Load secrets
        domain = _get_secrets('QINIU_Domain')
        folder = _normalize_folder(_get_secrets('QINIU_Folder'))
        access_key = _get_secrets('QINIU_Accesskey')
        secret_key = _get_secrets('QINIU_SecretKey')
        bucket = 'source'  # fixed as per user instruction

        if not all([domain, access_key, secret_key]):
            logger.warning('Qiniu secrets are missing; skip upload.')
            return None

        # Fetch image bytes with anti-hotlink headers
        from urllib.parse import urlparse
        parsed = urlparse(image_url)
        domain_lower = parsed.netloc.lower()
        
        # 根据域名设置合适的 Referer
        if 'csdnimg.cn' in domain_lower or 'csdn.net' in domain_lower:
            referer = 'https://blog.csdn.net/'
        elif 'zhihu.com' in domain_lower or 'zhimg.com' in domain_lower:
            referer = 'https://www.zhihu.com/'
        elif 'jianshu.com' in domain_lower or 'jianshu.io' in domain_lower:
            referer = 'https://www.jianshu.com/'
        elif 'juejin.cn' in domain_lower or 'juejin.im' in domain_lower:
            referer = 'https://juejin.cn/'
        elif 'mmbiz.qpic.cn' in domain_lower or 'qq.com' in domain_lower:
            referer = 'https://mp.weixin.qq.com/'
        elif 'alicdn.com' in domain_lower or 'aliyuncs.com' in domain_lower:
            # 阿里云 OSS/CDN，使用阿里云开发者社区作为 Referer
            referer = 'https://developer.aliyun.com/'
        elif '51cto.com' in domain_lower:
            referer = 'https://www.51cto.com/'
        elif 'infoq.cn' in domain_lower or 'infoq.com' in domain_lower:
            referer = 'https://www.infoq.cn/'
        elif 'segmentfault.com' in domain_lower:
            referer = 'https://segmentfault.com/'
        else:
            referer = f"{parsed.scheme}://{parsed.netloc}/"
        
        # 构建请求头，模拟真实浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer,
            'Connection': 'keep-alive',
        }
        
        resp = requests.get(image_url, timeout=15, stream=True, headers=headers, verify=False)
        resp.raise_for_status()
        content = resp.content

        # Decide key
        ext = _guess_ext_from_url(image_url)
        key = _deterministic_key(image_url, ext, folder)

        # Build upload token
        token = _make_upload_token(access_key, secret_key, bucket, key)

        # Qiniu form upload endpoint
        # Allow override via secrets; otherwise use generic then auto-correct by error hint
        # Prefer explicit upload host, else infer from region, else default to z2
        upload_host = (
            _get_secrets('QINIU_UploadHost')
            or _host_for_region(_get_secrets('QINIU_Region'))
        )
        def _post_to_host(host: str):
            url = host if host.startswith('http') else f'https://{host}'
            files = {
                'file': ('blob' + ext, content, 'application/octet-stream')
            }
            data = {
                'token': token,
                'key': key,
            }
            return requests.post(url, data=data, files=files, timeout=30)

        up = _post_to_host(upload_host)
        if up.status_code in (200, 614):
            return f"{domain}{key}"

        # Handle incorrect region hint: "incorrect region, please use up-z2.qiniup.com"
        if up.status_code == 400 and 'incorrect region' in up.text:
            try:
                # naive parse of suggested host
                # extract last token that looks like a hostname
                text = up.text
                # find 'use ' and take following token
                marker = 'use '
                idx = text.find(marker)
                if idx >= 0:
                    host_part = text[idx + len(marker):].strip().strip('"').strip('.')
                else:
                    host_part = 'upload.qiniup.com'
                logger.info(f"Retrying Qiniu upload with suggested region host: {host_part}")
                up2 = _post_to_host(host_part)
                if up2.status_code in (200, 614):
                    return f"{domain}{key}"
                else:
                    logger.error(f"Qiniu upload failed after retry: {up2.status_code} {up2.text}")
            except Exception as e2:
                logger.error(f"Qiniu region retry error: {e2}")

        logger.error(f"Qiniu upload failed: {up.status_code} {up.text}")
        return None
    except Exception as e:
        logger.error(f"Qiniu upload exception: {e}")
        return None


def ensure_public_image_url(image_url: str) -> str:
    """
    Ensure the image URL is publicly embeddable in Markdown.
    If the URL appears to be a Baidu/CDN-protected link, try to re-host on Qiniu.
    Returns the original URL on failure.
    """
    try:
        if not image_url:
            return image_url
        if is_protected_cdn_url(image_url):
            new_url = upload_image_from_url(image_url)
            if new_url:
                logger.info(f"Rehosted protected image to Qiniu: {new_url}")
                return new_url
        return image_url
    except Exception:
        return image_url
