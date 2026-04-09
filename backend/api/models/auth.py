# -*- coding: utf-8 -*-
"""
认证相关 Pydantic 模型
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: "UserInfo" = Field(..., description="用户信息")


class UserInfo(BaseModel):
    """用户信息"""
    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    display_name: Optional[str] = Field(None, description="显示名称")
    avatar: Optional[str] = Field(None, description="头像 URL")
    bio: Optional[str] = Field(None, description="个人简介")
    is_admin: bool = Field(default=False, description="是否为超级管理员")
    membership_tier: str = Field(default="free", description="会员等级")

    class Config:
        from_attributes = True


class OAuthCallbackRequest(BaseModel):
    """OAuth 回调请求"""
    code: str = Field(..., description="授权码")
    state: Optional[str] = Field(None, description="状态参数")


class BindEmailRequest(BaseModel):
    """绑定邮箱请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, max_length=100, description="密码")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")


class OAuthAccountInfo(BaseModel):
    """OAuth 账号信息"""
    provider: str = Field(..., description="提供商")
    provider_user_id: str = Field(..., description="提供商用户 ID")
    created_at: str = Field(..., description="绑定时间")


class UserProfileResponse(BaseModel):
    """用户完整资料响应"""
    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    display_name: Optional[str] = Field(None, description="显示名称")
    avatar: Optional[str] = Field(None, description="头像 URL")
    bio: Optional[str] = Field(None, description="个人简介")
    has_password: bool = Field(..., description="是否设置了密码")
    oauth_accounts: list[OAuthAccountInfo] = Field(default_factory=list, description="已绑定的 OAuth 账号")


class UpdateAvatarRequest(BaseModel):
    """更新头像请求"""
    avatar_url: str = Field(..., description="新的头像 URL（七牛云返回的 URL）")


class UpdateAvatarResponse(BaseModel):
    """更新头像响应"""
    avatar_url: str = Field(..., description="更新后的头像 URL")
    avatar_source: str = Field(default="manual", description="头像来源")


class UpdateProfileRequest(BaseModel):
    """更新个人资料请求"""
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
