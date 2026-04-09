# -*- coding: utf-8 -*-
"""
SupaWriter API 核心安全模块
JWT Token 生成/验证、密码哈希、OAuth
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
import hashlib
import os
import logging

from backend.api.config import settings

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    密码哈希（使用 bcrypt）

    兼容现有的 SHA256 方式，但新用户使用更安全的 bcrypt
    bcrypt 有 72 字节限制，对于超长密码先用 SHA256 预处理
    """
    # bcrypt 有 72 字节限制
    # 对于正常密码（<72字节）直接使用 bcrypt
    # 对于超长密码，先用 SHA256 预处理
    if len(password.encode('utf-8')) > 72:
        # 使用 SHA256 预处理超长密码
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # 使用 bcrypt 哈希密码
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    支持 bcrypt 和 SHA256 两种哈希方式（兼容现有用户）
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 先尝试 bcrypt 验证
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$"):
        try:
            # bcrypt 有 72 字节限制
            # 如果密码超过 72 字节，使用 SHA256 预处理（与 hash_password 保持一致）
            password_to_verify = plain_password
            if len(plain_password.encode('utf-8')) > 72:
                password_to_verify = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
            
            logger.debug(f"Verifying bcrypt password, hash prefix: {hashed_password[:10]}")
            logger.debug(f"Password length: {len(plain_password)}, bytes: {len(plain_password.encode('utf-8'))}")
            
            # 使用 bcrypt 验证
            password_bytes = password_to_verify.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            result = bcrypt.checkpw(password_bytes, hashed_bytes)
            
            logger.debug(f"Bcrypt verification result: {result}")
            return result
        except Exception as e:
            # 如果出错，记录错误并返回 False
            logger.error(f"Password verification error: {e}", exc_info=True)
            return False

    # 兼容旧的 SHA256 方式
    logger.debug(f"Using SHA256 verification, hash: {hashed_password[:20]}...")
    sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return sha256_hash == hashed_password


def create_access_token(
    user_id: int,
    extra_data: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT access token

    Args:
        user_id: 用户 ID
        extra_data: 额外的数据（可选）
        expires_delta: 过期时间增量（可选）

    Returns:
        JWT token 字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)

    # payload 数据
    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    # 添加额外数据
    if extra_data:
        payload.update(extra_data)

    # 生成 token
    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 payload，如果 token 无效则返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.warning(f"Token expired: {e}")
        return None
    except Exception as e:
        # Handle any JWT related errors
        error_type = type(e).__name__
        if 'ExpiredSignatureError' in error_type or 'expired' in str(e).lower():
            logger.warning(f"Token expired: {e}")
        elif 'InvalidSignatureError' in error_type or 'signature' in str(e).lower():
            logger.warning(f"Invalid token signature (secret key mismatch): {e}")
        elif 'InvalidTokenError' in error_type or 'invalid' in str(e).lower():
            logger.warning(f"Invalid token format: {e}")
        else:
            logger.warning(f"JWT decode error: {error_type}: {e}")
        return None


def verify_token(token: str) -> Optional[int]:
    """
    验证 token 并返回用户 ID

    Args:
        token: JWT token 字符串

    Returns:
        用户 ID，如果 token 无效则返回 None
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Verifying token (first 20 chars): {token[:20]}...")
    
    payload = decode_token(token)
    if payload is None:
        logger.warning("Token decode failed")
        return None

    logger.info(f"Token payload: {payload}")
    
    # 检查 token 类型
    if payload.get("type") != "access":
        logger.warning(f"Invalid token type: {payload.get('type')}")
        return None

    # 返回用户 ID
    user_id = payload.get("user_id")
    logger.info(f"Token verified successfully, user_id: {user_id}")
    return user_id


def create_refresh_token(user_id: int) -> str:
    """
    创建 refresh token（用于刷新 access token）

    Args:
        user_id: 用户 ID

    Returns:
        Refresh token 字符串
    """
    expire = datetime.utcnow() + timedelta(days=60)  # 60 天有效期

    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def verify_refresh_token(token: str) -> Optional[int]:
    """
    验证 refresh token 并返回用户 ID

    Args:
        token: Refresh token 字符串

    Returns:
        用户 ID，如果 token 无效则返回 None
    """
    payload = decode_token(token)
    if payload is None:
        return None

    if payload.get("type") != "refresh":
        return None

    return payload.get("user_id")


def create_oauth_state(
    user_id: Optional[int] = None,
    frontend: Optional[str] = None
) -> str:
    """
    创建 OAuth state 参数（防止 CSRF 攻击）

    Args:
        user_id: 用户 ID（可选，用于绑定账号）
        frontend: 前端类型（可选，'creator' 或 'community'）

    Returns:
        State 字符串
    """
    import secrets
    import time

    state_data = {
        "nonce": secrets.token_urlsafe(32),
        "timestamp": int(time.time()),
        "user_id": user_id,
        "frontend": frontend
    }

    # 编码为 base64
    import base64
    import json

    state_json = json.dumps(state_data)
    state_bytes = state_json.encode('utf-8')
    state_b64 = base64.urlsafe_b64encode(state_bytes).decode('utf-8')

    return state_b64


def verify_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    """
    验证 OAuth state 参数

    Args:
        state: State 字符串

    Returns:
        State 数据，如果无效则返回 None
    """
    import base64
    import json
    import time

    try:
        # 解码 base64
        state_bytes = base64.urlsafe_b64decode(state.encode('utf-8'))
        state_json = state_bytes.decode('utf-8')
        state_data = json.loads(state_json)

        # 检查时间戳（10分钟内有效）
        timestamp = state_data.get("timestamp", 0)
        if time.time() - timestamp > 600:
            return None

        return state_data
    except Exception:
        return None
