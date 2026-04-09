# -*- coding: utf-8 -*-
"""API 密钥加密/解密工具"""

from cryptography.fernet import Fernet
from typing import Optional
import base64
import os
import logging

logger = logging.getLogger(__name__)


def _get_encryption_key() -> str:
    """获取加密密钥（从多个来源尝试）"""
    # 优先从环境变量获取
    key = os.getenv("ENCRYPTION_KEY", "")

    # 如果环境变量没有，尝试从配置文件读取
    if not key:
        try:
            from backend.api.config import settings
            key = settings.ENCRYPTION_KEY
        except ImportError:
            pass

    return key


class EncryptionManager:
    """密钥加密管理器"""

    def __init__(self, key: Optional[str] = None):
        """初始化加密管理器"""
        self.key = key or _get_encryption_key()

        if not self.key:
            # 如果没有配置密钥，生成一个（仅用于开发）
            self.key = Fernet.generate_key().decode()
            logger.warning("⚠️ 未配置 ENCRYPTION_KEY，使用临时密钥")

        if isinstance(self.key, str):
            self.key = self.key.encode()

        try:
            self.cipher = Fernet(self.key)
        except Exception as e:
            logger.error(f"加密器初始化失败: {e}")
            # 生成新密钥作为后备
            self.key = Fernet.generate_key()
            self.cipher = Fernet(self.key)

    def encrypt(self, plaintext: str) -> str:
        """加密明文"""
        if not plaintext:
            return ""
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise ValueError(f"加密失败: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """解密密文"""
        if not ciphertext:
            return ""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise ValueError(f"解密失败: {e}")

    def generate_preview(self, api_key: str, visible_chars: int = 4) -> str:
        """生成 API 密钥预览"""
        if not api_key:
            return ""
        if api_key.startswith("sk-") or api_key.startswith("sk_"):
            prefix = api_key[:3]
            suffix = api_key[-visible_chars:] if len(api_key) > visible_chars else ""
            return f"{prefix}{'*' * 8}{suffix}"
        else:
            suffix = api_key[-visible_chars:] if len(api_key) > visible_chars else api_key
            return f"{'*' * 8}{suffix}"


# 全局实例
encryption_manager = EncryptionManager()
