# -*- coding: utf-8 -*-
"""
Google OAuth 认证路由 - 用于 NextAuth 集成
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import logging

from backend.api.core.security import create_access_token
from backend.api.models.auth import TokenResponse, UserInfo
from utils.database import Database

logger = logging.getLogger(__name__)
router = APIRouter()


class GoogleAuthRequest(BaseModel):
    """Google 认证请求"""
    google_id: str
    email: str
    name: str
    picture: str | None = None


@router.post("/google", response_model=TokenResponse)
async def google_auth(request_data: GoogleAuthRequest):
    """
    Google OAuth 认证
    
    前端使用 NextAuth 完成 Google 登录后，将用户信息发送到此接口
    后端验证并返回 JWT token
    
    Args:
        request_data: Google 用户信息
        
    Returns:
        Token 响应，包含 access_token 和用户信息
    """
    try:
        with Database.get_cursor() as cursor:
            # 检查用户是否已存在（通过 Google ID）
            cursor.execute("""
                SELECT u.id, u.username, u.email, u.display_name
                FROM users u
                JOIN oauth_accounts oa ON u.id = oa.user_id
                WHERE oa.provider = 'google' AND oa.provider_user_id = %s
            """, (request_data.google_id,))
            
            user = cursor.fetchone()
            
            if user:
                # 用户已存在，直接返回 token
                logger.info(f"Existing Google user logged in: {user['email']}")
            else:
                # 新用户，创建账号
                # 先检查邮箱是否已被使用
                cursor.execute("SELECT id FROM users WHERE email = %s", (request_data.email,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    # 邮箱已存在，绑定 Google 账号
                    user_id = existing_user['id']
                    cursor.execute("""
                        INSERT INTO oauth_accounts (user_id, provider, provider_user_id, access_token)
                        VALUES (%s, 'google', %s, '')
                        ON CONFLICT (provider, provider_user_id) DO NOTHING
                    """, (user_id, request_data.google_id))
                    
                    cursor.execute("""
                        SELECT id, username, email, display_name
                        FROM users WHERE id = %s
                    """, (user_id,))
                    user = cursor.fetchone()
                    
                    logger.info(f"Bound Google account to existing user: {request_data.email}")
                else:
                    # 创建新用户
                    # 生成唯一的 username
                    base_username = request_data.email.split('@')[0]
                    username = base_username
                    counter = 1
                    
                    while True:
                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        if not cursor.fetchone():
                            break
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    # 插入用户
                    cursor.execute("""
                        INSERT INTO users (username, email, display_name, auth_method)
                        VALUES (%s, %s, %s, 'oauth')
                        RETURNING id, username, email, display_name
                    """, (username, request_data.email, request_data.name))
                    
                    user = cursor.fetchone()
                    
                    # 创建 OAuth 账号关联
                    cursor.execute("""
                        INSERT INTO oauth_accounts (user_id, provider, provider_user_id, access_token)
                        VALUES (%s, 'google', %s, '')
                    """, (user['id'], request_data.google_id))
                    
                    logger.info(f"New Google user created: {request_data.email}")
            
            # 生成后端 JWT token
            access_token = create_access_token(user['id'])
            
            # 构建用户信息
            user_info = UserInfo(
                id=user['id'],
                username=user['username'],
                email=user['email'],
                display_name=user.get('display_name'),
                avatar=request_data.picture,  # 使用 Google 提供的头像
                bio=None
            )
            
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_info
            )
            
    except Exception as e:
        logger.error(f"Google auth error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )
