# -*- coding: utf-8 -*-
"""
SupaWriter 认证路由
处理用户注册、登录、登出、OAuth
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.requests import Request as StarletteRequest
from typing import Optional
import logging
import os

from backend.api.models.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserInfo,
    OAuthCallbackRequest,
    BindEmailRequest,
    ChangePasswordRequest,
    UserProfileResponse,
    OAuthAccountInfo,
    UpdateAvatarRequest,
    UpdateAvatarResponse,
    UpdateProfileRequest
)
from backend.api.core.security import (
    create_access_token,
    create_oauth_state,
    verify_oauth_state,
    hash_password,
    verify_password
)
from backend.api.core.dependencies import get_current_user, get_current_user_optional, get_db
from backend.api.config import settings
from backend.api.services.user import UserService
from backend.api.repositories.user import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


def _user_to_user_info(user_dict: dict) -> UserInfo:
    """
    Convert user dict from database to UserInfo response model.

    Args:
        user_dict: User data from database

    Returns:
        UserInfo instance
    """
    # Check if user is superuser based on email and is_superuser flag
    from backend.api.services.tier_service import TierService, get_super_admin_emails
    email = user_dict.get('email', '')
    is_superuser = user_dict.get('is_superuser', False)
    super_admin_emails = get_super_admin_emails()
    is_admin = email in super_admin_emails and is_superuser

    return UserInfo(
        id=user_dict.get('id'),
        username=user_dict.get('username'),
        email=user_dict.get('email'),
        display_name=user_dict.get('display_name'),
        avatar=user_dict.get('avatar_url'),
        bio=user_dict.get('motto'),
        is_admin=is_admin,
        membership_tier=user_dict.get('membership_tier', 'free')
    )


async def get_user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    user_repo = UserRepository(session)
    return UserService(session, user_repo)


@router.post("/register", response_model=TokenResponse)
async def register(
    request_data: RegisterRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    用户注册

    使用邮箱和密码注册新用户

    Args:
        request_data: 注册请求数据
        user_service: User service instance

    Returns:
        Token 响应，包含 access_token 和用户信息

    Raises:
        HTTPException: 注册失败时
    """
    # 调用注册服务
    user = await user_service.register_user(
        username=request_data.username,
        email=request_data.email,
        password=request_data.password,
        display_name=request_data.display_name
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Username or email may already exist."
        )

    # 生成 access token
    access_token = create_access_token(user.id)

    # 构建用户信息
    user_info = _user_to_user_info({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'display_name': user.display_name,
        'avatar_url': user.avatar_url,
        'motto': user.motto,
        'is_superuser': user.is_superuser,
        'membership_tier': user.membership_tier,
    })

    logger.info(f"User registered: {user.username}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_info
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request_data: LoginRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    用户登录

    使用邮箱和密码登录

    Args:
        request_data: 登录请求数据
        user_service: User service instance

    Returns:
        Token 响应，包含 access_token 和用户信息

    Raises:
        HTTPException: 登录失败时
    """
    # 调用登录服务
    user = await user_service.authenticate_user(
        email=request_data.email,
        password=request_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 生成 access token
    access_token = create_access_token(user.id)

    # 构建用户信息
    user_info = _user_to_user_info({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'display_name': user.display_name,
        'avatar_url': user.avatar_url,
        'motto': user.motto,
        'is_superuser': user.is_superuser,
        'membership_tier': user.membership_tier,
    })

    logger.info(f"User logged in: {user.username}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_info
    )


@router.post("/logout")
async def logout(current_user_id: int = Depends(get_current_user)):
    """
    用户登出

    客户端应该删除本地存储的 token

    Args:
        current_user_id: 当前用户 ID

    Returns:
        成功消息
    """
    # 在 JWT 模式下，登出主要由客户端处理（删除 token）
    # 这里可以添加额外的登出逻辑，比如：
    # - 将 token 加入黑名单
    # - 清除服务端 session
    # - 记录登出日志等

    logger.info(f"User logged out: user_id={current_user_id}")

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取当前用户信息

    Args:
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        用户信息
    """
    user_profile = await user_service.get_user_profile(current_user_id)

    if user_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return _user_to_user_info(user_profile)


# ===== OAuth 认证 =====

@router.get("/oauth/{provider}")
async def oauth_login(
    provider: str,
    request: Request,
    frontend: Optional[str] = "creator"
):
    """
    OAuth 登录入口

    重定向到 OAuth 提供商的授权页面

    Args:
        provider: OAuth 提供商（google, wechat）
        request: FastAPI Request 对象
        frontend: 前端类型（creator 或 community）

    Returns:
        重定向响应

    Raises:
        HTTPException: 不支持的提供商时
    """
    if provider not in ["google", "wechat"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )

    # 导入 OAuth 配置
    from authlib.integrations.starlette_client import OAuth
    import urllib.parse

    # 创建 OAuth 实例
    oauth = OAuth()

    # 注册 OAuth 客户端
    if provider == "google":
        oauth.register(
            name='google',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
    elif provider == "wechat":
        oauth.register(
            name='wechat',
            client_id=settings.WECHAT_APPID,
            client_secret=settings.WECHAT_SECRET,
            authorize_url='https://open.weixin.qq.com/connect/qrconnect',
            access_token_url='https://api.weixin.qq.com/sns/oauth2/access_token',
            client_kwargs={'scope': 'snsapi_login'}
        )

    # 生成 state 参数（将 frontend 编码到 state 中）
    state = create_oauth_state(frontend=frontend)

    # 确定回调 URL - 简化版本，不带查询参数
    # Google 要求 redirect_uri 必须与 Google Cloud Console 中配置的完全匹配
    # frontend 信息现在通过 state 参数传递
    scheme = request.url.scheme
    host = request.url.netloc
    redirect_uri = f"{scheme}://{host}/api/v1/auth/oauth/callback/{provider}"

    # 重定向到 OAuth 提供商
    if provider == "google":
        return await oauth.google.authorize_redirect(request, redirect_uri, state=state)
    elif provider == "wechat":
        # 微信需要额外参数
        auth_url = (
            f"https://open.weixin.qq.com/connect/qrconnect"
            f"?appid={settings.WECHAT_APPID}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
            f"&response_type=code"
            f"&scope=snsapi_login"
            f"&state={state}#wechat_redirect"
        )
        return RedirectResponse(url=auth_url)


@router.get("/oauth/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str,
    state: Optional[str] = None,
    user_service: UserService = Depends(get_user_service)
):
    """
    OAuth 回调处理

    处理 OAuth 提供商的回调，完成登录流程

    Args:
        provider: OAuth 提供商
        request: FastAPI Request 对象
        code: 授权码
        state: 状态参数（包含 frontend 信息）
        user_service: User service instance

    Returns:
        重定向到前端，携带 token
    """
    from authlib.integrations.starlette_client import OAuth

    # 验证 state 并获取其中的数据
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing state parameter"
        )

    state_data = verify_oauth_state(state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter"
        )

    # 从 state 中获取 frontend 类型（默认为 creator）
    frontend = state_data.get("frontend", "creator")

    # 创建 OAuth 实例
    oauth = OAuth()

    if provider == "google":
        oauth.register(
            name='google',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )

        # 获取 token
        token = await oauth.google.authorize_access_token(request)
        user_info = token['userinfo']

        # 准备 OAuth 用户数据
        oauth_data = {
            'provider': 'google',
            'provider_user_id': user_info.get('sub'),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture')
        }

        # 登录或注册
        user = await user_service.oauth_login(oauth_data)

    elif provider == "wechat":
        # 微信 OAuth 处理
        # 这里需要实现微信 OAuth 流程
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="WeChat OAuth not yet implemented"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}"
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth login failed"
        )

    # 生成 JWT token
    access_token = create_access_token(user.id)

    # 确定重定向 URL
    if frontend == "community":
        frontend_url = settings.COMMUNITY_URL
    else:
        frontend_url = settings.CREATOR_URL

    # 重定向到前端回调页面
    callback_url = f"{frontend_url}/auth/callback?token={access_token}"

    logger.info(f"OAuth login successful: {user.username} via {provider}")

    return RedirectResponse(url=callback_url)


@router.post("/oauth/verify-token")
async def verify_oauth_token(
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    验证 OAuth token

    用于前端定期验证 token 是否有效

    Args:
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        用户信息
    """
    user_profile = await user_service.get_user_profile(current_user_id)

    if user_profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return _user_to_user_info(user_profile)


# ===== 账号绑定和管理 =====

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取用户完整资料

    包含已绑定的 OAuth 账号信息

    Args:
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        用户完整资料
    """
    user_profile = await user_service.get_profile_with_oauth(current_user_id)

    if user_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    oauth_list = [
        OAuthAccountInfo(
            provider=oa["provider"],
            provider_user_id=oa["provider_user_id"],
            created_at=oa["created_at"]
        )
        for oa in user_profile.get("oauth_accounts", [])
    ]

    return UserProfileResponse(
        id=user_profile.get('id'),
        username=user_profile.get('username'),
        email=user_profile.get('email'),
        display_name=user_profile.get('display_name'),
        avatar=user_profile.get('avatar_url'),
        bio=user_profile.get('motto'),
        has_password=user_profile.get('has_password', False),
        oauth_accounts=oauth_list
    )


@router.post("/bind-email")
async def bind_email(
    request_data: BindEmailRequest,
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    为当前用户绑定邮箱和密码

    允许 OAuth 用户添加邮箱密码作为备用登录方式

    Args:
        request_data: 绑定邮箱请求
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        成功消息
    """
    try:
        result = await user_service.bind_email(
            user_id=current_user_id,
            email=request_data.email,
            password=request_data.password
        )
        logger.info(f"User {current_user_id} bound email: {request_data.email}")
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/change-password")
async def change_password(
    request_data: ChangePasswordRequest,
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    修改密码

    Args:
        request_data: 修改密码请求
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        成功消息
    """
    success = await user_service.update_password(
        user_id=current_user_id,
        old_password=request_data.old_password,
        new_password=request_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password update failed. Check your old password."
        )

    logger.info(f"User {current_user_id} changed password successfully")

    return {"message": "Password changed successfully"}


@router.put("/update-avatar", response_model=UpdateAvatarResponse)
async def update_avatar(
    request_data: UpdateAvatarRequest,
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    更新用户头像（通过 URL）

    允许用户手动设置头像，设置后将标记 avatar_source 为 'manual'
    之后的 OAuth 登录将不再覆盖此头像

    Args:
        request_data: 更新头像请求（包含七牛云返回的 URL）
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        更新后的头像信息
    """
    # 更新头像并设置来源为 manual
    user = await user_service.update_profile(
        user_id=current_user_id,
        avatar_url=request_data.avatar_url
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 更新 avatar_source 为 manual（直接执行 SQL）
    from backend.api.core.dependencies import get_db
    async for db in get_db():
        from sqlalchemy import text
        await db.execute(
            text("UPDATE users SET avatar_source = 'manual' WHERE id = :user_id"),
            {"user_id": current_user_id}
        )
        await db.commit()
        break

    logger.info(f"User {current_user_id} updated avatar manually")

    return UpdateAvatarResponse(
        avatar_url=user.avatar_url or "",
        avatar_source="manual"
    )


@router.post("/upload-avatar", response_model=UpdateAvatarResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    上传用户头像到七牛云

    Args:
        file: 上传的图片文件（支持 jpg, png, gif, webp，最大 5MB）
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        更新后的头像信息
    """
    from backend.api.services.avatar import AvatarUploadService

    # 上传到七牛云
    avatar_url = await AvatarUploadService.upload_avatar(current_user_id, file)

    # 更新用户头像
    user = await user_service.update_profile(
        user_id=current_user_id,
        avatar_url=avatar_url
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 更新 avatar_source 为 manual
    from backend.api.core.dependencies import get_db
    async for db in get_db():
        from sqlalchemy import text
        await db.execute(
            text("UPDATE users SET avatar_source = 'manual' WHERE id = :user_id"),
            {"user_id": current_user_id}
        )
        await db.commit()
        break

    logger.info(f"User {current_user_id} uploaded new avatar")

    return UpdateAvatarResponse(
        avatar_url=avatar_url,
        avatar_source="manual"
    )


@router.put("/update-profile")
async def update_profile(
    request_data: UpdateProfileRequest,
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    更新用户资料（显示名称、个人简介）

    Args:
        request_data: 更新资料请求
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        成功消息
    """
    user = await user_service.update_profile(
        user_id=current_user_id,
        display_name=request_data.display_name,
        motto=request_data.bio
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    logger.info(f"User {current_user_id} updated profile")

    return {"message": "Profile updated successfully"}


@router.delete("/unbind-oauth/{provider}")
async def unbind_oauth(
    provider: str,
    current_user_id: int = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    解绑 OAuth 账号

    必须保留至少一种登录方式（密码或其他 OAuth）

    Args:
        provider: OAuth 提供商名称 (google, wechat, github)
        current_user_id: 当前用户 ID
        user_service: User service instance

    Returns:
        成功消息
    """
    try:
        result = await user_service.unbind_oauth(
            user_id=current_user_id,
            provider=provider
        )
        logger.info(f"User {current_user_id} unbound {provider} OAuth")
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
