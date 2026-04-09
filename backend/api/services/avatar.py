# -*- coding: utf-8 -*-
"""
Avatar Upload Service
Handles avatar image upload to Qiniu Cloud
"""

import logging
import os
import base64
import hashlib
import time
import hmac
import json
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)


class AvatarUploadService:
    """Service for uploading user avatars to Qiniu Cloud"""

    # Default settings
    DEFAULT_BUCKET = 'source'
    DEFAULT_FOLDER = 'avatars/'
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
    }

    @staticmethod
    def _get_qiniu_config() -> dict:
        """Get Qiniu configuration from environment or database"""
        from backend.api.utils.backend_settings import get_system_setting

        config = {
            'domain': os.getenv('QINIU_Domain') or get_system_setting('qiniu.domain', ''),
            'folder': os.getenv('QINIU_Folder') or get_system_setting('qiniu.folder', 'avatars/'),
            'access_key': os.getenv('QINIU_Accesskey') or get_system_setting('qiniu.access_key', ''),
            'secret_key': os.getenv('QINIU_SecretKey') or get_system_setting('qiniu.secret_key', ''),
            'region': os.getenv('QINIU_Region') or get_system_setting('qiniu.region', 'z2'),
            'bucket': os.getenv('QINIU_Bucket') or get_system_setting('qiniu.bucket', 'source'),
        }

        # Normalize folder
        folder = config['folder'].strip()
        if folder and not folder.endswith('/'):
            folder += '/'
        config['folder'] = folder or 'avatars/'

        return config

    @staticmethod
    def _urlsafe_b64encode(data: bytes) -> str:
        """URL-safe base64 encode"""
        return base64.urlsafe_b64encode(data).decode().strip()

    @staticmethod
    def _make_upload_token(access_key: str, secret_key: str, bucket: str, key: str, expires: int = 3600) -> str:
        """Generate Qiniu upload token"""
        put_policy = {
            'scope': f'{bucket}:{key}',
            'deadline': int(time.time()) + expires,
        }
        policy = json.dumps(put_policy, separators=(',', ':')).encode()
        encoded_policy = AvatarUploadService._urlsafe_b64encode(policy)
        sign = hmac.new(secret_key.encode(), encoded_policy.encode(), hashlib.sha1).digest()
        encoded_sign = AvatarUploadService._urlsafe_b64encode(sign)
        return f"{access_key}:{encoded_sign}:{encoded_policy}"

    @staticmethod
    def _get_upload_host(region: str) -> str:
        """Map Qiniu region code to upload host"""
        mapping = {
            'z0': 'upload.qiniup.com',
            'z1': 'upload-z1.qiniup.com',
            'z2': 'up-z2.qiniup.com',
            'na0': 'upload-na0.qiniup.com',
            'as0': 'upload-as0.qiniup.com',
        }
        return mapping.get(region.strip().lower(), 'up-z2.qiniup.com')

    @staticmethod
    def _generate_avatar_key(user_id: int, filename: str, folder: str) -> str:
        """Generate unique upload key for avatar"""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in AvatarUploadService.ALLOWED_EXTENSIONS:
            ext = '.jpg'

        # Use timestamp + user_id for unique key
        timestamp = int(time.time())
        key = f"{folder}avatar_{user_id}_{timestamp}{ext}"
        return key

    @staticmethod
    async def upload_avatar(user_id: int, file: UploadFile) -> str:
        """
        Upload avatar image to Qiniu Cloud

        Args:
            user_id: User ID
            file: Uploaded file

        Returns:
            Public URL of uploaded avatar

        Raises:
            HTTPException: If upload fails
        """
        # Validate file size
        content = await file.read()
        if len(content) > AvatarUploadService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {AvatarUploadService.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # Reset file pointer
        await file.seek(0)

        # Validate MIME type
        content_type = file.content_type
        if content_type not in AvatarUploadService.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(AvatarUploadService.ALLOWED_MIME_TYPES)}"
            )

        # Get Qiniu config
        config = AvatarUploadService._get_qiniu_config()

        if not all([config['access_key'], config['secret_key'], config['domain']]):
            raise HTTPException(
                status_code=500,
                detail="Qiniu storage is not configured properly"
            )

        # Generate upload key
        key = AvatarUploadService._generate_avatar_key(user_id, file.filename or 'avatar.jpg', config['folder'])

        # Generate upload token
        token = AvatarUploadService._make_upload_token(
            config['access_key'],
            config['secret_key'],
            config['bucket'],
            key
        )

        # Upload to Qiniu
        upload_host = AvatarUploadService._get_upload_host(config['region'])
        upload_url = f"https://{upload_host}"

        try:
            files = {
                'file': (file.filename or 'avatar.jpg', content, content_type)
            }
            data = {
                'token': token,
                'key': key,
            }

            response = requests.post(upload_url, data=data, files=files, timeout=30)

            if response.status_code in (200, 614):  # 614 means file already exists (same key)
                # Return public URL
                public_url = f"{config['domain']}{key}"
                logger.info(f"Avatar uploaded successfully for user {user_id}: {public_url}")
                return public_url

            # Handle region error
            if response.status_code == 400 and 'incorrect region' in response.text:
                raise HTTPException(
                    status_code=500,
                    detail=f"Qiniu region mismatch. Please configure the correct region."
                )

            logger.error(f"Qiniu upload failed: {response.status_code} {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload avatar: {response.text}"
            )

        except requests.RequestException as e:
            logger.error(f"Avatar upload network error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Network error while uploading avatar"
            )

    @staticmethod
    def delete_avatar(url: str) -> bool:
        """
        Delete avatar from Qiniu Cloud (if needed in the future)

        Args:
            url: Public URL of the avatar

        Returns:
            True if deleted successfully, False otherwise
        """
        # This would require Qiniu API client with proper authentication
        # For now, we just log - avatars can be garbage collected later
        logger.info(f"Avatar marked for deletion: {url}")
        return True


# Convenience function for base64 encoded avatar upload
async def upload_avatar_base64(user_id: int, base64_data: str) -> str:
    """
    Upload avatar from base64 encoded data

    Args:
        user_id: User ID
        base64_data: Base64 encoded image data (with or without data:image/...;base64, prefix)

    Returns:
        Public URL of uploaded avatar
    """
    import re

    # Remove data URL prefix if present
    match = re.match(r'data:image/(\w+);base64,(.+)', base64_data)
    if match:
        ext = f".{match.group(1)}"
        data = base64.b64decode(match.group(2))
    else:
        # Try to decode as raw base64
        try:
            data = base64.b64decode(base64_data)
            ext = '.jpg'  # Default extension
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # Create a mock file object
    class MockFile:
        def __init__(self, data: bytes, filename: str, content_type: str):
            self.data = data
            self.filename = filename
            self.content_type = content_type

        async def read(self):
            return self.data

        async def seek(self, pos):
            pass  # No-op for in-memory data

    # Determine content type from extension
    content_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    content_type = content_type_map.get(ext.lower(), 'image/jpeg')

    mock_file = MockFile(data, f"avatar{ext}", content_type)

    # Use the service
    return await AvatarUploadService.upload_avatar(user_id, mock_file)  # type: ignore
