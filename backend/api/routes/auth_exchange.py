# -*- coding: utf-8 -*-
"""
Token Exchange Route
Exchange frontend OAuth session for backend JWT token
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict
import logging
import os

from backend.api.models.auth import UserInfo
from backend.api.core.security import create_access_token
from utils.database import User, OAuthAccount

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_user_info(user: Dict) -> UserInfo:
    email = user.get('email', '')
    is_superuser = user.get('is_superuser', False)
    super_admin_emails = [
        value.strip()
        for value in os.getenv('SUPER_ADMIN_EMAILS', 'wxk952718180@gmail.com').split(',')
        if value.strip()
    ]
    is_admin = email in super_admin_emails and is_superuser

    return UserInfo(
        id=user['id'],
        username=user['username'],
        email=user['email'],
        display_name=user.get('display_name'),
        avatar=user.get('avatar_url'),
        bio=user.get('motto'),
        is_admin=is_admin,
        membership_tier=user.get('membership_tier', 'free'),
    )


def _derive_base_username(email: str) -> str:
    base = email.split('@')[0].strip()
    return base or "user"


def _build_unique_username(base_username: str) -> str:
    candidate = base_username
    suffix = 1

    while User.get_user_by_username(candidate) is not None:
        candidate = f"{base_username}_{suffix}"
        suffix += 1

    return candidate


def _find_existing_user(request: "ExchangeTokenRequest") -> Optional[Dict]:
    if request.google_id:
        existing_oauth = OAuthAccount.get_oauth_account('google', request.google_id)
        if existing_oauth is not None:
            user = User.get_user_by_id(existing_oauth['user_id'])
            if user is not None:
                return user

    if request.user_id:
        user = User.get_user_by_id(request.user_id)
        if user is not None:
            return user

    return User.get_user_by_email(request.email)


def _create_exchange_user(request: "ExchangeTokenRequest") -> Dict:
    base_username = _derive_base_username(request.email)

    for _ in range(20):
        username = _build_unique_username(base_username)
        user_id = User.create_user(
            username=username,
            email=request.email,
            display_name=request.name,
            avatar_url=request.picture,
            avatar_source='google' if request.picture else None
        )

        if user_id is not None:
            user = User.get_user_by_id(user_id)
            if user is not None:
                return user
            break

        # Handle concurrent creation or duplicate email by re-checking the authoritative record.
        existing_user = User.get_user_by_email(request.email)
        if existing_user is not None:
            return existing_user

        logger.warning("Retrying OAuth user creation after username conflict for %s", request.email)

    logger.error(f"Failed to create user for email: {request.email}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create user account"
    )


class ExchangeTokenRequest(BaseModel):
    """Token exchange request"""
    email: str
    name: Optional[str] = None
    google_id: Optional[str] = None
    user_id: Optional[int] = None  # 后端用户 ID（用于已有用户）
    picture: Optional[str] = None


class ExchangeTokenResponse(BaseModel):
    """Token exchange response"""
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


@router.post("/exchange-token", response_model=ExchangeTokenResponse)
async def exchange_token(request: ExchangeTokenRequest):
    """
    Exchange frontend OAuth session for backend JWT token

    This endpoint allows the frontend (using NextAuth with Google OAuth)
    to obtain a backend JWT token for API calls.

    If the user doesn't exist in the database, they will be created automatically.

    Args:
        request: Token exchange request with user info from NextAuth

    Returns:
        JWT token and user info
    """
    user = _find_existing_user(request)

    if user is None:
        logger.info(f"Creating new user for email: {request.email}")
        user = _create_exchange_user(request)

        # If we have a google_id, create OAuth account binding
        if request.google_id:
            google_user_info = {
                'sub': request.google_id,
                'email': request.email,
                'name': request.name,
                'picture': request.picture
            }
            OAuthAccount.create_oauth_account(
                user_id=user['id'],
                provider='google',
                provider_user_id=request.google_id,
                extra_data=google_user_info
            )
    else:
        # 用户已存在
        # 自动关联 OAuth 账号（如果提供了 google_id 且尚未绑定）
        if request.google_id:
            existing_oauth = OAuthAccount.get_oauth_account('google', request.google_id)
            if existing_oauth is None:
                # 该 Google 账号尚未绑定到任何用户，自动关联到当前用户
                google_user_info = {
                    'sub': request.google_id,
                    'email': request.email,
                    'name': request.name,
                    'picture': request.picture
                }
                OAuthAccount.create_oauth_account(
                    user_id=user['id'],
                    provider='google',
                    provider_user_id=request.google_id,
                    extra_data=google_user_info
                )
                logger.info(f"Auto-linked Google OAuth to existing user: {user['username']}")

        # 更新显示名称和头像（带优先级逻辑）
        # 头像优先级：
        # 1. 如果用户已手动设置头像 (avatar_source = 'manual')，不覆盖
        # 2. 如果用户当前没有头像，使用 Google 头像
        # 3. 如果用户当前是 Google 头像 (avatar_source = 'google')，可以更新
        if request.picture or request.name:
            from utils.database import Database
            with Database.get_cursor() as cursor:
                # 先查询当前用户的 avatar_source
                cursor.execute("SELECT avatar_url, avatar_source FROM users WHERE id = %s", (user['id'],))
                current = cursor.fetchone()
                current_avatar_source = current['avatar_source'] if current else None

                update_fields = []
                update_values = []

                # 头像更新逻辑：只在没有头像或来源是 google 时更新
                if request.picture:
                    if current_avatar_source is None or current_avatar_source == 'google':
                        update_fields.append("avatar_url = %s")
                        update_fields.append("avatar_source = 'google'")
                        update_values.append(request.picture)
                        logger.info(f"Updated Google avatar for user: {user['username']}")
                    elif current_avatar_source == 'manual':
                        logger.info(f"Skipping avatar update for user with manual avatar: {user['username']}")

                if request.name:
                    update_fields.append("display_name = %s")
                    update_values.append(request.name)

                if update_fields:
                    update_values.append(user['id'])
                    query = f"""
                        UPDATE users
                        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                    cursor.execute(query, update_values)
                    logger.info(f"Updated user info for: {user['username']}")

                    # 重新获取用户信息以获取最新数据
                    user = User.get_user_by_id(user['id'])

    # Generate JWT token
    access_token = create_access_token(user['id'])

    # Update last login time
    User.update_last_login(user['id'])

    user_info = _build_user_info(user)

    logger.info(f"Token exchanged for user: {user['username']}")

    return ExchangeTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_info
    )
